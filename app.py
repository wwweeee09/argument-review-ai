# -*- coding: utf-8 -*-
"""
吵架复盘AI应用 - 完整后端
支持多说话人识别（最多10人）+ 结合上下文的逐句分析
"""
from flask import Flask , render_template , request , jsonify , Response , stream_with_context
from flask_cors import CORS
import os
import uuid
import json
import logging
import time
import requests
import base64
from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment
from typing import Dict , Optional , Callable , Generator

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建Flask应用
app = Flask(__name__)
CORS(app)

# 配置
app.config[ 'UPLOAD_FOLDER' ] = 'uploads'
app.config[ 'MAX_CONTENT_LENGTH' ] = 100 * 1024 * 1024

os.makedirs(app.config[ 'UPLOAD_FOLDER' ] , exist_ok=True)

# 说话人颜色映射（支持最多10个说话人）
SPEAKER_COLORS = {
    0 : '#667eea' , 1 : '#f093fb' , 2 : '#4ecdc4' , 3 : '#ff6b6b' ,
    4 : '#f9ca24' , 5 : '#6c5ce7' , 6 : '#a8e6cf' , 7 : '#ff8c94' ,
    8 : '#95e77e' , 9 : '#d4a5a5'
}

ASR_MODELS = {
    "8953" : {"name" : "中文话者分离模型" , "pid" : 8953 , "description" : "支持区分说话人，最多识别10人" ,
              "speaker_diarization" : True , "max_speakers" : 10}
}


class BaiduVoiceQualityAPI :
    def __init__(self , api_key: str , secret_key: str) :
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None

    def get_access_token(self) -> str :
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {"grant_type" : "client_credentials" , "client_id" : self.api_key , "client_secret" : self.secret_key}
        try :
            response = requests.post(url , params=params , timeout=10)
            data = response.json()
            if "access_token" in data :
                self.access_token = data[ "access_token" ]
                return self.access_token
            return None
        except Exception as e :
            logger.error(f"获取token失败: {e}")
            return None

    def create_detection_task_with_base64(self , speech_data_base64: str , session_id: str , pid: int = 8953 ,
                                          callback=None) -> Dict :
        token = self.get_access_token()
        if not token :
            return {"success" : False , "error" : "无法获取access_token"}
        url = "https://aip.baidubce.com/rest/2.0/speech/publiccloudspeech/v1/voice/detection"
        payload = {
            "access_token" : token , "speech_data" : speech_data_base64 , "session_id" : session_id ,
            "sample_rate" : 16000 , "pid" : pid , "enable_detection" : False , "enable_detection_detail" : False
        }
        if pid == 8953 :
            payload[ "is_split_channel" ] = False
        headers = {"Content-Type" : "application/json"}
        try :
            response = requests.post(url , json=payload , headers=headers , timeout=60)
            result = response.json()
            if result.get("error_code") == 0 :
                return {"success" : True , "session_id" : result.get("result" , {}).get("session_id" , session_id)}
            return {"success" : False , "error" : result.get("error_message" , "创建失败")}
        except Exception as e :
            return {"success" : False , "error" : str(e)}

    def query_detection_result(self , session_id: str) -> Dict :
        token = self.get_access_token()
        if not token :
            return {"success" : False , "error" : "无法获取access_token"}
        url = f"https://aip.baidubce.com/rest/2.0/speech/publiccloudspeech/v1/voice/detection/result?access_token={token}&session_id={session_id}"
        try :
            response = requests.get(url , timeout=30)
            result = response.json()
            if result.get("error_code") != 0 :
                return {"success" : False , "error" : result.get("error_message")}
            result_data = result.get("result" , {})
            state_desc = result_data.get("state_desc" , "")
            if state_desc == "处理成功" or result_data.get("asr_result") :
                asr_result = result_data.get("asr_result" , [ ])
                sentences_with_speaker = [ ]
                speakers_set = set()
                for item in asr_result :
                    sentence = item.get("sentence" , "")
                    speaker_id = item.get("speaker_id" , 0)
                    if sentence :
                        sentences_with_speaker.append({"speaker" : speaker_id , "text" : sentence})
                        speakers_set.add(speaker_id)
                full_text = "。".join([ s[ "text" ] for s in sentences_with_speaker ])
                return {"success" : True , "status" : "completed" , "text" : full_text ,
                        "sentences_with_speaker" : sentences_with_speaker , "speaker_count" : len(speakers_set)}
            elif state_desc in [ "任务已提交，排队等待中" , "执行中" ] :
                return {"success" : True , "status" : "processing"}
            return {"success" : False , "error" : f"处理失败: {state_desc}"}
        except Exception as e :
            return {"success" : False , "error" : str(e)}

    def wait_for_result(self , session_id: str , max_wait_time: int = 120 , callback=None) -> Dict :
        start_time = time.time()
        while time.time() - start_time < max_wait_time :
            result = self.query_detection_result(session_id)
            if result.get("status") == "completed" :
                return result
            elif result.get("status") == "failed" or not result.get("success") :
                return result
            time.sleep(2)
        return {"success" : False , "error" : "识别超时"}


class AudioProcessor :
    @staticmethod
    def convert_to_pcm(audio_file: str , output_pcm: str) -> tuple :
        try :
            audio = AudioSegment.from_file(audio_file)
            duration = len(audio) / 1000
            if audio.channels > 1 :
                audio = audio.set_channels(1)
            if audio.frame_rate != 16000 :
                audio = audio.set_frame_rate(16000)
            if audio.sample_width != 2 :
                audio = audio.set_sample_width(2)
            audio = audio.normalize()
            audio.export(output_pcm , format="s16le")
            return True , duration
        except Exception as e :
            logger.error(f"音频转换失败: {e}")
            return False , 0

    @staticmethod
    def get_base64_data(pcm_file_path: str) -> str :
        with open(pcm_file_path , 'rb') as f :
            return base64.b64encode(f.read()).decode('utf-8')


class DeepSeekAnalyzer :
    def __init__(self , api_key: str) :
        self.client = OpenAI(api_key=api_key , base_url="https://api.deepseek.com")

    def analyze_single_sentence_with_context(self , sentence: str , sentence_index: int ,
                                             total_sentences: int , speaker: int ,
                                             full_conversation: str ,
                                             thinking_mode: bool = True ,
                                             reasoning_effort: str = "high") -> Generator :
        """结合完整上下文分析单句话"""
        speaker_text = f"说话人{speaker}" if speaker >= 0 else "未知"

        # 构建完整的对话上下文
        system_prompt = f"""你是一位专业的沟通分析和冲突调解专家。请基于整个对话的上下文语境，对当前这句话进行深入分析。

【完整对话内容】：
{full_conversation}

【当前需要分析的句子】：
这是第 {sentence_index}/{total_sentences} 句话，由{speaker_text}说出。
当前句子："{sentence}"

【分析要求】：
请结合整个对话的语境，对这句话进行全面分析：

1. **情绪分析**：这句话表达了什么情绪？情绪的强度如何？结合前后文，情绪是否有变化？
2. **逻辑分析**：这句话是否存在逻辑问题？是否有前后矛盾？是否是在回应对方？
3. **沟通模式分析**：这句话属于什么类型的表达？（防御型、攻击型、回避型、建设型等）
4. **语境作用**：这句话在整体对话中起到了什么作用？是火上浇油还是试图缓和？
5. **改进建议**：基于整个对话的语境，如何换种方式表达会更好？

请用温暖、专业的语气输出，每部分用简短的要点说明，总字数控制在200字以内。"""

        messages = [
            {"role" : "system" , "content" : system_prompt} ,
            {"role" : "user" , "content" : f"请结合整个对话的上下文，分析第{sentence_index}句话：{sentence}"}
        ]

        try :
            params = {"model" : "deepseek-chat" , "messages" : messages , "stream" : True}
            if thinking_mode :
                params[ "reasoning_effort" ] = reasoning_effort
                params[ "extra_body" ] = {"thinking" : {"type" : "enabled"}}
            else :
                params[ "temperature" ] = 0.7
            response = self.client.chat.completions.create(**params)
            for chunk in response :
                if chunk.choices and chunk.choices[ 0 ].delta.content :
                    yield {"type" : "content" , "content" : chunk.choices[ 0 ].delta.content}
            yield {"type" : "complete"}
        except Exception as e :
            yield {"type" : "error" , "content" : str(e)}

    def analyze_overall(self , sentences_with_speaker: list , speaker_count: int ,
                        thinking_mode: bool = True , reasoning_effort: str = "high") -> Generator :
        conversation = ""
        speaker_stats = {}
        for item in sentences_with_speaker :
            speaker = item.get("speaker" , 0)
            text = item.get("text" , "")
            conversation += f"[说话人{speaker}] {text}\n"
            speaker_stats[ speaker ] = speaker_stats.get(speaker , 0) + 1
        system_prompt = f"""对话共有{speaker_count}位说话人。请进行综合分析（500-1000字）：

{conversation}

请输出：1.对话概览 2.各说话人立场分析 3.核心矛盾点 4.改进建议（分人）5.总结评分。使用Markdown格式。"""
        messages = [ {"role" : "system" , "content" : system_prompt} , {"role" : "user" , "content" : "请综合分析"} ]
        try :
            params = {"model" : "deepseek-chat" , "messages" : messages , "stream" : True}
            if thinking_mode :
                params[ "reasoning_effort" ] = reasoning_effort
                params[ "extra_body" ] = {"thinking" : {"type" : "enabled"}}
            else :
                params[ "temperature" ] = 0.7
            response = self.client.chat.completions.create(**params)
            for chunk in response :
                if chunk.choices and chunk.choices[ 0 ].delta.content :
                    yield {"type" : "content" , "content" : chunk.choices[ 0 ].delta.content}
            yield {"type" : "complete"}
        except Exception as e :
            yield {"type" : "error" , "content" : str(e)}

    def chat_stream(self , message: str , transcript: str = "" , thinking_mode: bool = True ,
                    reasoning_effort: str = "high") -> Generator :
        system_prompt = f"对话内容：{transcript[ :1500 ]}\n\n用户问题：{message}\n\n请友好回答。"
        messages = [ {"role" : "system" , "content" : system_prompt} , {"role" : "user" , "content" : message} ]
        try :
            params = {"model" : "deepseek-chat" , "messages" : messages , "stream" : True}
            if thinking_mode :
                params[ "reasoning_effort" ] = reasoning_effort
                params[ "extra_body" ] = {"thinking" : {"type" : "enabled"}}
            else :
                params[ "temperature" ] = 0.7
            response = self.client.chat.completions.create(**params)
            for chunk in response :
                if chunk.choices and chunk.choices[ 0 ].delta.content :
                    yield {"type" : "content" , "content" : chunk.choices[ 0 ].delta.content}
            yield {"type" : "complete"}
        except Exception as e :
            yield {"type" : "error" , "content" : str(e)}


AI_API_KEY = os.getenv('BAIDU_API_KEY' , '')
AI_SECRET_KEY = os.getenv('BAIDU_SECRET_KEY' , '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY' , '')

asr_client = BaiduVoiceQualityAPI(api_key=AI_API_KEY , secret_key=AI_SECRET_KEY)
deepseek = DeepSeekAnalyzer(api_key=DEEPSEEK_API_KEY)


@app.route('/')
def index() :
    return render_template('index.html')


@app.route('/api/models' , methods=[ 'GET' ])
def get_models() :
    return jsonify(ASR_MODELS)


@app.route('/api/upload' , methods=[ 'POST' ])
def upload_audio() :
    try :
        if 'audio' not in request.files :
            return jsonify({'error' : '没有音频文件'}) , 400
        audio_file = request.files[ 'audio' ]
        file_id = str(uuid.uuid4())
        original_path = os.path.join(app.config[ 'UPLOAD_FOLDER' ] , f"{file_id}_original.mp3")
        audio_file.save(original_path)
        pcm_path = os.path.join(app.config[ 'UPLOAD_FOLDER' ] , f"{file_id}.pcm")
        success , duration = AudioProcessor.convert_to_pcm(original_path , pcm_path)
        if not success :
            return jsonify({'error' : '音频转换失败'}) , 400
        return jsonify({'file_id' : file_id , 'duration' : duration})
    except Exception as e :
        return jsonify({'error' : str(e)}) , 500


@app.route('/api/recognize/<file_id>' , methods=[ 'POST' ])
def recognize_audio(file_id) :
    try :
        pcm_path = os.path.join(app.config[ 'UPLOAD_FOLDER' ] , f"{file_id}.pcm")
        if not os.path.exists(pcm_path) :
            return jsonify({'error' : '文件不存在'}) , 404
        session_id = f"asr_{file_id}_{int(time.time())}"
        speech_base64 = AudioProcessor.get_base64_data(pcm_path)
        result = asr_client.create_detection_task_with_base64(speech_base64 , session_id , pid=8953)
        if not result.get("success") :
            return jsonify({'error' : result.get("error" , "创建失败")}) , 500
        final_result = asr_client.wait_for_result(session_id , max_wait_time=120)
        if not final_result or not final_result.get("success") :
            return jsonify({'error' : final_result.get("error" , "识别失败")}) , 500
        return jsonify(
            {
                'text' : final_result.get("text" , "") ,
                'sentence_count' : len(final_result.get("sentences_with_speaker" , [ ])) ,
                'speaker_count' : final_result.get("speaker_count" , 0) ,
                'sentences_with_speaker' : final_result.get("sentences_with_speaker" , [ ])
            })
    except Exception as e :
        return jsonify({'error' : str(e)}) , 500


@app.route('/api/analyze_sentence' , methods=[ 'POST' ])
def analyze_sentence() :
    """逐句分析API - 结合完整上下文"""
    try :
        data = request.get_json()
        sentence = data.get('sentence' , '')
        sentence_index = data.get('sentence_index' , 0)
        total_sentences = data.get('total_sentences' , 0)
        speaker = data.get('speaker' , -1)
        thinking_mode = data.get('thinking_mode' , True)
        reasoning_effort = data.get('reasoning_effort' , 'high')
        full_conversation = data.get('full_conversation' , '')  # 获取完整对话上下文

        if not sentence :
            return jsonify({'error' : '没有句子内容'}) , 400

        def generate() :
            # 如果没有传入完整对话，使用默认提示
            if full_conversation :
                for chunk in deepseek.analyze_single_sentence_with_context(
                        sentence , sentence_index , total_sentences , speaker ,
                        full_conversation , thinking_mode , reasoning_effort
                ) :
                    yield f"data: {json.dumps(chunk , ensure_ascii=False)}\n\n"
            else :
                # 兼容旧版本
                speaker_text = f"说话人{speaker}" if speaker >= 0 else "未知"
                system_prompt = f"""【强制要求】这是第 {sentence_index}/{total_sentences} 句话，由{speaker_text}说出。

请分析：1.情绪 2.逻辑问题 3.攻击性语言 4.改进建议。直接输出，200字以内。"""
                messages = [
                    {"role" : "system" , "content" : system_prompt} ,
                    {"role" : "user" , "content" : f"请分析第{sentence_index}句话：{sentence}"}
                ]
                try :
                    params = {"model" : "deepseek-chat" , "messages" : messages , "stream" : True}
                    if thinking_mode :
                        params[ "reasoning_effort" ] = reasoning_effort
                        params[ "extra_body" ] = {"thinking" : {"type" : "enabled"}}
                    else :
                        params[ "temperature" ] = 0.7
                    response = deepseek.client.chat.completions.create(**params)
                    for chunk in response :
                        if chunk.choices and chunk.choices[ 0 ].delta.content :
                            yield f"data: {json.dumps({'type' : 'content' , 'content' : chunk.choices[ 0 ].delta.content})}\n\n"
                except Exception as e :
                    yield f"data: {json.dumps({'type' : 'error' , 'content' : str(e)})}\n\n"
            yield "data: {\"type\": \"end\"}\n\n"

        return Response(
            stream_with_context(generate()) ,
            mimetype='text/event-stream' ,
            headers={'Cache-Control' : 'no-cache' , 'X-Accel-Buffering' : 'no'}
        )
    except Exception as e :
        return jsonify({'error' : str(e)}) , 500


@app.route('/api/analyze_overall' , methods=[ 'POST' ])
def analyze_overall() :
    try :
        data = request.get_json()
        sentences_with_speaker = data.get('sentences_with_speaker' , [ ])
        speaker_count = data.get('speaker_count' , 0)
        thinking_mode = data.get('thinking_mode' , True)
        reasoning_effort = data.get('reasoning_effort' , 'high')

        def generate() :
            for chunk in deepseek.analyze_overall(
                    sentences_with_speaker , speaker_count , thinking_mode , reasoning_effort) :
                yield f"data: {json.dumps(chunk , ensure_ascii=False)}\n\n"
            yield "data: {\"type\": \"end\"}\n\n"

        return Response(stream_with_context(generate()) , mimetype='text/event-stream')
    except Exception as e :
        return jsonify({'error' : str(e)}) , 500


@app.route('/api/chat/stream' , methods=[ 'POST' ])
def chat_stream() :
    try :
        data = request.get_json()
        message = data.get('message' , '')
        thinking_mode = data.get('thinking_mode' , True)
        reasoning_effort = data.get('reasoning_effort' , 'high')
        transcript = data.get('transcript' , '')

        def generate() :
            for chunk in deepseek.chat_stream(message , transcript , thinking_mode , reasoning_effort) :
                yield f"data: {json.dumps(chunk , ensure_ascii=False)}\n\n"
            yield "data: {\"type\": \"end\"}\n\n"

        return Response(stream_with_context(generate()) , mimetype='text/event-stream')
    except Exception as e :
        return jsonify({'error' : str(e)}) , 500


if __name__ == '__main__' :
    print("\n" + "=" * 60)
    print("🎭 吵架复盘AI应用 - 支持多说话人（最多10人）")
    print("=" * 60)
    print("✅ 百度ASR: 已配置")
    print("✅ DeepSeek: 已配置")
    print("\n📌 多说话人支持:")
    print("   - 自动识别2-10个不同说话人")
    print("   - 每个说话人用不同颜色标记")
    print("\n📌 逐句分析增强:")
    print("   - 结合完整对话上下文进行分析")
    print("   - 分析情绪、逻辑、沟通模式、语境作用")
    print("\n🌐 访问地址: http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=True , port=5000)