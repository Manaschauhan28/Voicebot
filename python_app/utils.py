from stream2sentence import generate_sentences
import boto3
import json, re, random
import pymysql
import os
from botocore.exceptions import ClientError
import sqlite3
import concurrent.futures
from datetime import datetime
import pytz

# Define IST timezone
ist = pytz.timezone('Asia/Kolkata')

client = boto3.client('bedrock-runtime')
ses_client = boto3.client('ses')
sns_client = boto3.client('sns')
comprehend_client = boto3.client('comprehend')
translate_client = boto3.client('translate')

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Database credentials
# host = os.environ.get('HOST')
# port = int(os.environ.get('PORT'))
# user = os.environ.get('USER')
# password = os.environ.get('PASSWORD')
# database = os.environ.get('MYSQL_DATABASE')
# tablename = os.environ.get('TABLENAME')



language_selection_prompt = """
You are a Customer Support Executive working for Swiftly Holdings. When interacting with users, you have to respond with "How may I help you today?" in the input language of user.
Examples:
User: Hey I need you to speak in English.
Assistant: Hello, How may I help you today?

User: Hi there, can you assist me in English?
Assistant: Hello, How may I help you today?

User: Hablemos en español
Assistant: Hola, ¿En qué puedo ayudarte hoy en español?

User: Necesito ayuda en español por favor
Assistant: Hola, ¿En qué puedo ayudarte hoy en español?
"""

english_starting_list = [
"Hello! How can I assist you today?",
"Hi there, how may I help you?",
"Hey! What can I do for you today?",
"Hey! Need any help today?",
"Hello, is there anything I can help you with?",
]

spanish_starting_list = [
"¡Hola! ¿Cómo puedo ayudarte hoy?",
"¡Hola! ¿En qué puedo ayudarte?",
"¡Buenos días! ¿Qué puedo hacer por ti hoy?",
"¡Hey! ¿Necesitas ayuda hoy?",
"¡Hola! ¿Hay algo en lo que te pueda ayudar?",
]




def read_lines(file_path: str):
    """
    Read each line in a text file and return a list of texts.

    Args:
    - file_path (str): The path to the text file.

    Returns:
    - List[str]: A list containing each line of text from the file.
    """
    texts = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            texts.append(line.strip())
    return texts

def get_faq_prompt(language):
    if language == "es" :
        with open("faq_prompt_es.txt", encoding="utf-8") as f:
            prompt = f.read()
    else :
        with open("faq_prompt.txt", encoding="utf-8") as f:
            prompt = f.read()
    print(" FAQ is calling...")
    # with open("faq_prompt.txt") as f :
    #     prompt = f.read()
    instructions = f"""{prompt}"""
    return instructions

def get_prompt(language):
    if language == "es" :
        with open("prompt_es.txt", encoding="utf-8") as f:
            prompt = f.read()
    else :
        with open("prompt.txt", encoding="utf-8") as f:
            prompt = f.read()
    instructions = f"""
    {prompt} 
    """

    return instructions


# Create a thread executor
executor = concurrent.futures.ThreadPoolExecutor()
# Function to translate text
def translate_text(text, source_lang, target_lang):
    response = translate_client.translate_text(
        Text=text,
        SourceLanguageCode=source_lang,
        TargetLanguageCode=target_lang
    )
    return response['TranslatedText']

# Function to insert chat data into SQLite3
def insert_chat_log(call_sid,mobile_number, interaction, model_prompt, bot_response, language):
    # Background function
    def _insert():
        conn = sqlite3.connect('chat_logs.db')
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_sid TEXT,
                mobile_number TEXT,
                time TEXT,
                interaction TEXT,
                user_input_spanish TEXT,
                bot_response_spanish TEXT,
                user_input_english TEXT,
                bot_response_english TEXT
            )
        ''')
        conn.commit()

        user_input = ""
        if isinstance(model_prompt, list) and len(model_prompt) > 0:
            for message in reversed(model_prompt):
                if message.get("role") == "user":
                    user_input = message.get("content", "")
                break
        # Translate if Spanish
        if language == 'es':
            user_input_english = translate_text(user_input, source_lang='es', target_lang='en')
            bot_response_english = translate_text(bot_response, source_lang='es', target_lang='en')
            user_input_spanish = user_input
            bot_response_spanish = bot_response
        else:  # English
            user_input_spanish = None
            bot_response_spanish = None
            user_input_english = user_input
            bot_response_english = bot_response
        time = datetime.now(ist)
        time = time.strftime('%Y-%m-%d %H:%M:%S')
        # Insert data
        cursor.execute('''
            INSERT INTO chat_logs (
                call_sid, mobile_number,time, interaction, 
                user_input_spanish, bot_response_spanish, 
                user_input_english, bot_response_english
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (call_sid,mobile_number,time, interaction, user_input_spanish, bot_response_spanish, user_input_english, bot_response_english))

        conn.commit()
        conn.close()

    # Run the insert in background
    executor.submit(_insert)
def split_into_sentences(text):
    # Split on ., ?, ! followed by space or end of string, keep punctuation as part of sentence
    sentences = re.split(r'(?<=[.?!])\s+', text.strip())
    # Clean sentences (strip extra whitespace)
    return [s.strip() for s in sentences if s.strip()]

def clean_input_questions(conversation):
    cleaned_conversation = []
    previous_user_contents = []

    for i, entry in enumerate(conversation):
        role = entry.get('role')
        content = entry.get('content', '').strip()

        if role == 'user':
            current_user_content = content
            print(" Current Content :- ", current_user_content)

            # Split current message into sentences
            current_sentences = split_into_sentences(current_user_content)

            # Remove sentences that appeared before
            filtered_sentences = []
            for sentence in current_sentences:
                if sentence not in previous_user_contents:
                    filtered_sentences.append(sentence)

            # Join back the filtered sentences if any
            if filtered_sentences:
                cleaned_text = ' '.join(filtered_sentences)
                cleaned_conversation.append({'role': role, 'content': cleaned_text})

                # Add these sentences to previous_user_contents
                previous_user_contents.extend(filtered_sentences)

                # Keep only last 10 sentences (you can adjust the number)
                if len(previous_user_contents) > 3:
                    previous_user_contents = previous_user_contents[-3:]

                print(previous_user_contents)
            else:
                # If nothing new remains, you can skip adding or add empty message
                pass
        else:
            cleaned_conversation.append({'role': role, 'content': content})
    new_data = cleaned_conversation[-12:]
    if new_data[0].get('role') == "user":
        return new_data
    return cleaned_conversation[-13:]


def yield_sentences( call_sid,phone_number, context: str, faq_prompt, language, interaction,language_selection):
    # yield from chat_with_ai(context)
    for sentence in generate_sentences(
        chat_with_ai(call_sid,phone_number,context, faq_prompt, language,interaction, language_selection),
        minimum_sentence_length=10,
    ):
    
        print(sentence) 
        yield sentence



#### For Avoiding System Errors from Bedrock. 

def ensure_alternating_roles(data):
    # If the data is empty, return it immediately
    if not data:
        return data
    
    # Create a new list to store the corrected data
    corrected_data = [data[0]]  # Initialize with the first item
    
    # Iterate through the remaining items in the data
    for item in data[1:]:
        # Check if the current item's role is different from the last item in corrected_data
        if item['role'] != corrected_data[-1]['role']:
            corrected_data.append(item)
    
    return corrected_data





def chat_with_ai(call_sid,phone_number, model_prompt, faq_prompt, language, interaction, language_selection):
    if language is None :
        language = detectlanguagebycomprehend(model_prompt)
    if language_selection is True : 
        stream = random.choice(english_starting_list) if language == "en" else random.choice(spanish_starting_list)
        print("System Fixed ",stream)
    else :
        if faq_prompt is False : system_prompt = get_prompt(language)
        else : system_prompt = get_faq_prompt(language)
        print("Faq prompt Prompt called ", faq_prompt)
        model_prompt = ensure_alternating_roles(model_prompt)
        print("===>>>",model_prompt)
        # app.udate_chat(model_prompt)
        # feed_transcription(model_prompt)
        model_prompt = clean_input_questions(model_prompt)
        request=json.dumps(
                    {
                    "anthropic_version":"bedrock-2023-05-31", 
                    "max_tokens":256,
                    "temperature":0.2,
                    "system":system_prompt,
                    "messages":model_prompt
                    }
                )
        # print(request)
        response = client.invoke_model(
            # model="llama-3.1-70b-versatile",
            modelId=MODEL_ID, 
            body=request,
            accept = 'application/json',
            contentType = 'application/json'
        )
        print(response)
        response = json.loads(response.get('body').read())
        # print("====>>>", response)
        stream = response['content'][0]['text'] 
        insert_chat_log(call_sid,phone_number, interaction, model_prompt, stream, language)
        print("Model Generated", stream)   
    for chunk in stream:
        if not chunk:
            continue 
        yield chunk
    



def judge_end(model_prompt):
    system_prompt = """<task_description>
Your task:
Classify each incoming user message as either a conversation continuation (output: 0) or a conversation termination (output: 1).

Base your classification only on the most recent user message.

Use specific linguistic cues, explicit statements, and overall sentiment to guide your decision, prioritizing explicit over implicit signals.
</task_description>

<criteria_for_output_1>
Output 1 (Conversation Termination)
Classify as 1 only if the user’s message signals intent to end the conversation through one or more of the following:

a. Explicit Endings:

Phrases such as: "bye", "goodbye", "end call", "hang up", "that's all", "nothing else", "we're done", "thanks, that's all", "thank you, goodbye", "no further questions".

b. Task or Request Completion:

Expressions like: "got it", "all set", "that helps, thanks", "perfect, thanks", "exactly what I needed", "received it", "I’ll contact later", "call back if needed".

c. Frustration or Disengagement:

Clear messages of dissatisfaction: "this isn't helping", "waste of time", "never mind", "forget it", "I'm done", "I'll try something else".

d. Natural Conclusion:

Confirmation of receipt, no pending requests, or acknowledgement of completed tasks/goals, with no additional questions or topics.

Notes:

If a pleasantry (e.g., "thank you") is not paired with an explicit end signal, do not classify as output 1.
</criteria_for_output_1>

<criteria_for_output_0>
Output 0 (Conversation Continuation)
Classify as 0 in any of the following situations:

a. Active Participation:

Follow-up questions, requests for clarification or examples, new topics, or requests for more details (e.g., "What about...", "How do I...", "Can you explain...", "Could you send...").

b. Ongoing Engagement:

Responses connecting to previous messages, partial understanding ("I'm not sure", "Could you repeat?"), or evidence of incomplete resolution.

c. No Explicit End Signal:

Ambiguous responses ("Okay", "Yes", "No", "Sure", "Alright").

Simple instructions or requests ("send it via mail", "I want it in English").
</criteria_for_output_0>

<response_rules>

Consider only the latest user message.

Explicit signals always override implied meaning.

If ambiguous or unclear, default to output: 0 (continuation).

Pleasantries alone do not imply termination.

Do not infer based on message tone unless negative sentiment is explicit or repeated.

If user requests sending something (e.g., "send it by mail"), treat as continuation unless paired with a closing statement.
</response_rules>

<output_format>

json
{
  "output": [0 or 1],
  "confidence": "high"|"medium"|"low"
}
</output_format>

<examples> 
Input: "Thanks, that's all I needed." 
Output: {"output": 1, "confidence": "high"}

Input: "What about my insurance card?"
Output: {"output": 0, "confidence": "high"}

Input: "Okay"
Output: {"output": 0, "confidence": "low"}

Input: "This is useless, I'm done."
Output: {"output": 1, "confidence": "high"}

Input: "I want to talk in English."
Output: {"output": 0, "confidence": "high"}

Input: "envíame por correo."
Output: {"output": 0, "confidence": "high"}

Input: "No. Send it via mail."
Output: {"output": 0, "confidence": "high"}
</examples>"""

    # model_prompt = ensure_alternating_roles(model_prompt)
    print("<<<===Query===>>>",model_prompt)
    # feed_transcription(model_prompt)
    request=json.dumps(
				{
				"anthropic_version":"bedrock-2023-05-31", 
				"max_tokens":50,
                "temperature":0.1,
				"system":system_prompt,
				"messages":[{"role":"user", "content": model_prompt}]
				}
			)
    # print(request)
    response = client.invoke_model(
        # model="llama-3.1-70b-versatile",
        modelId=MODEL_ID, 
		body=request,
		accept = 'application/json',
		contentType = 'application/json'
	)
    # print(response)
    response = json.loads(response.get('body').read())
    # print("====>>>", response)
    response = response['content'][0]['text'] 
    print("====Response Text ===>", response)
    return response



def judge_sms_email_sending(model_prompt):
    system_prompt = """Analyze a call transcript to identify the requested service and the preferred delivery mode (email, text, or both).

Service Requests:
- copy_policy → Policy document copy
- insurance_card → Insurance card copy
- proof_coverage → Coverage proof letter
- quote_copy → Quote copy
- loss_payee_form → Add loss payee
- mortgagee_form → Add mortgagee
- claim_assistance → Claim reporting help

Output Rules:
1. If no service is explicitly requested, return empty array for "name"
2. If no delivery mode is mentioned, return "none" for "mode"
3. Only include services that are explicitly mentioned in the conversation
4. Do not infer or guess services that weren't discussed

Output Format (JSON):
{
  "mode": "[email/text/both/none]",
  "name": ["copy_policy", "insurance_card", ...] // Empty array if no services requested
}

Example outputs:
- When no services mentioned: {"mode": "none", "name": []}
- When service mentioned but no mode: {"mode": "none", "name": ["copy_policy"]}
- When both mentioned: {"mode": "email", "name": ["copy_policy"]}
"""

    # model_prompt = ensure_alternating_roles(model_prompt)
    print("===>>>",model_prompt)
    # feed_transcription(model_prompt)
    request=json.dumps(
				{
				"anthropic_version":"bedrock-2023-05-31", 
				"max_tokens":150,
                "temperature":0.1,
				"system":system_prompt,
				"messages":[{"role":"user", 
                            "content": [{"type": "text", "text": str(model_prompt)}]
                            }]
				}
			)
    # print(request)
    response = client.invoke_model(
        # model="llama-3.1-70b-versatile",
        modelId=MODEL_ID, 
		body=request,
		accept = 'application/json',
		contentType = 'application/json'
	)
    # print(response)
    response = json.loads(response.get('body').read())
    # print("====>>>", response)
    response = response['content'][0]['text'] 
    print("== Final SMS Email response ==>", response)
    match = re.search(r'\{[\s\S]*?\}', response)
    if match : response = match.group() 
    else: response
    return response


def fetch_user_details(phone_number):
    # Connect to the database
    connection = pymysql.connect(
        host='swiftlyrds.c58swyaye4pe.us-east-1.rds.amazonaws.com',
        user='admin',
        password='Gr8#1job',
        database='swiftlyrds',
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with connection.cursor() as cursor:
            # Execute the query
            sql = "SELECT * FROM InsuranceData WHERE PhoneNumber = %s"
            cursor.execute(sql, (phone_number,))
            result = cursor.fetchone()
            print(result)
            return result
    finally:
        connection.close()




def send_sms(phone_number, user_name):
    """
    Send an SMS message to the specified phone number using AWS SNS.

    :param phone_number: The phone number to send the SMS to (in E.164 format, e.g., +14155552671).
    :param message: The message content to send.
    :return: The MessageId if the message was successfully sent.
    """
    if user_name == "Unknown User" : message = "Hello user, It seems you are not registered with us. Please make yourself registered then I will be able to provide you your requested documents"
    else : message = f"Hello {user_name}, PFA the link to access your requested documents from Swiftly. \n Thanks \n Sara"
    try:
        response = sns_client.publish(
            PhoneNumber=phone_number,
            Message=message,
        )
        print(f"Message sent! Message ID: {response['MessageId']}")
        return response['MessageId']
    except ClientError as e:
        print(f"Error sending SMS: {e.response['Error']['Message']}")
        return None


def send_email(to_address, user_name):
    subject = "Documents from Swiftly"
    body = f"Hello {user_name}, \n PFA your requested documents from Swiftly. \n\n Thanks & Regard \n Sara \n Customer Support Executive \n SWIFTLY Inc., U.S."
    try:
        response = ses_client.send_email(
            Source='aitest.stack@gmail.com',  # Replace with your verified email
            Destination={'ToAddresses': [to_address]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        print(f"Email Sent Message ID: {response['MessageId']}")
    
    except ClientError as e:
        # 
        print("Error in email Sending")


def detectlanguagebycomprehend(text):
    try:
        response = comprehend_client.detect_dominant_language(Text=str(text))
        lang_code = response["Languages"][0]["LanguageCode"]
        return lang_code
    except ClientError as e:
        return f"unknown error {e}"


# print(detectlanguagebycomprehend(" ¿cómo puedo obtener una copia de mi paliza?'"))


# model_prompt = "I need to obtain a copy of my policy"
# print(chat_with_ai("",False, "en",1,None))