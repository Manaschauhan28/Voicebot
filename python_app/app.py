import time
import json
import asyncio
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse, PlainTextResponse
from twilio.rest import Client
from twilio.twiml.voice_response import Gather, VoiceResponse
from utils import yield_sentences, judge_end, judge_sms_email_sending, send_email, send_sms, fetch_user_details, detectlanguagebycomprehend, ensure_alternating_roles

from pydantic import BaseModel
from typing import List
from pymongo import MongoClient
import os

account_sid = "ACae527ed8c3e8a11f2fef522ef234a860"
auth_token = "e0e9b15c28d3c0cfa53e04efcba65d13"

# account_sid = "AC9027d06799d81bc621b2b65e487d32b2"
# auth_token = "6557a9e34d6a3ddddfb702d43b7a8c34"

twilio_client = Client(account_sid, auth_token)

app = FastAPI()


uri = "mongodb+srv://manaschauhan:admin1234@swiftly-cluster.nw0zdfp.mongodb.net/?retryWrites=true&w=majority&appName=swiftly-cluster"
# Connect to MongoDB
client = MongoClient(uri, )
db = client["chat_data"]
collection = db["swiftly_poc"]

# Pydantic model for request validation
class ChatUpdateRequest(BaseModel):
    sid: str
    data: List[dict]  # List of chat messages [{"role": "user", "content": "Hello"}]

def update_chat(sid: str, messages: list):
    if not messages:
        raise ValueError("Message list cannot be empty")

    # Update the chat history (append multiple messages)
    result = collection.update_one(
        {"_id": sid},
        {
            "$push": {"chat_history": {"$each": messages}},  # Append all messages
        # Update last modified time
        },
        upsert=True  # Create a new document if SID does not exist
    )

    return {"message": "Chat updated"}


@app.get("/fetch_chat/")
async def fetch_chat(sid: str):
    chat_session = collection.find_one({"_id": sid}, {"_id": 0, "chat_history": 1})

    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return {"sid": sid, "chat_history": chat_session.get("chat_history", [])}

@app.post("/call_end")
async def call_end(call_sid: str):
    call = twilio_client.calls(call_sid).fetch()
    from_phone_number = call._from   # Caller phone number
    to_phone_number = call.to        # Recipient phone number
    call_duration = call.duration    # Call duration (in seconds) after call ends
    

    # store_call_data(call_duration, to_phone_number)
    twilio_client.calls(call_sid).update(status="completed")

user_session_data = {}
@app.post("/generate")
async def voice(request: Request):
    """Respond to incoming phone calls with a menu of options."""
    # Start our TwiML response
    try:
        language_selection = False
        body = await request.json()  # Parse the JSON body
        print("** Body **", body)
        model_prompt = body.get("content")
        print(model_prompt)
        call_sid = body.get("callSid")
        interaction = body.get("interactionCount")
        language = body.get("language")
        print(interaction, type(interaction))
        call = twilio_client.calls(call_sid).fetch()
        # from_phone_number = call._from   # Caller phone number
        print("In generate call_sid fetched ", call_sid)
        if call.to == "+18784255139": # Outgoing Calls
            phone_number = call._from # Reciever Number
        else : phone_number = call.to # Incoming Calls
        print("User's Phone Number :", phone_number)
        if int(interaction) == 0 :
            language_selection = True
            user_details = fetch_user_details(phone_number)
            user_session_data[call_sid] = {
                "user_details": user_details,
                "model_prompt": model_prompt
            }
        else : user_details = user_session_data.get(call_sid, {}).get("user_details")
        # print(" In generate User Details ", user_details)
        print("User Session Data :", user_session_data)
        if user_details is not None :
            faq_prompt = False
        else: faq_prompt = True
        if not model_prompt:
            return JSONResponse(
                status_code=400,
                content={"error": "The 'context' field is required in the request body."},
            )
        # Generate a stream of responses
        chat_stream = yield_sentences(call_sid,phone_number,model_prompt, faq_prompt, language,interaction,language_selection)
        # update_chat(call_sid, ensure_alternating_roles(model_prompt))
        return StreamingResponse(content=chat_stream, media_type="text/plain")
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request body. {str(e)}"},
        )
    


@app.post("/judge_ending")
async def judging_end(request: Request):
    try:
        body = await request.json()  # Parse the JSON body
        print("** Body **", body)
        model_prompt = body.get("content")
        if not model_prompt:
            return JSONResponse(
                status_code=400,
                content={"error": "The 'content' field is required in the request body."},
            )
        # Generate a stream of responses
        chat_stream = judge_end(model_prompt)
        return StreamingResponse(content=chat_stream, media_type="text/plain") 
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request body. {str(e)}"},
        )
          

#This function plays a crucial role in sending SMS or emails to users who calls.
@app.post("/judge_sms_email")
async def judge_sms_email(request:Request):
    try:
        body = await request.json()  # Parse the JSON body
        print("** Body **", body)
        model_prompt = body.get("content")
        call_sid = body.get("callSid")
        call = twilio_client.calls(call_sid).fetch()
        # from_phone_number = call._from   # Caller phone number
        print(len(call.to))
        if call.to == "+18784255139": # Outgoing Calls
            phone_number = call._from # Reciever Number
        else : phone_number = call.to # Incoming Calls

    
        if not model_prompt:
            return JSONResponse(
                status_code=400,
                content={"error": "The 'content' field is required in the request body."},
            )
        # Generate a stream of responses
        chat_stream = judge_sms_email_sending(model_prompt)
    
        data = json.loads(chat_stream) 
        # print("Resultant Data -->", data)
        print("User's Phone Number = ",phone_number)
        user_data = user_session_data.get(call_sid, {}).get("user_details")
        if user_data is None : 
            user_name = "Unknown User"
            user_email = " "
        else : 
            user_name = user_data['InsuredName']
            user_email = user_email = user_data['Email']
        print("User's Name = ",user_name)
        print("User's Email = ",user_email)
        to_check_mode = data.get('mode',"").lower()
        print(to_check_mode)
        if to_check_mode == "mail" and user_email != " ":
            send_email(user_email, user_name)
            response_text ="sending mail..."
        elif to_check_mode =="text":
            send_sms(phone_number, user_name)
            response_text ="Sending text..."
        elif to_check_mode =="both":
            send_sms(phone_number, user_name)
            send_email(user_email, user_name)
            response_text ="sending both mail & text"
        else:
            response_text ="No function get called"
        return JSONResponse(
            status_code=200,
            content=response_text
        )
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request body. {str(e)}"},
        )
    

@app.post("/detectlanguage")
async def detectlanguage(request : Request):
    try:
        body = await request.json()  # Parse the JSON body
        print("** Body **", body)
        text = body.get("content")
        if not text:
            return JSONResponse(
                status_code=400,
                content={"error": "The 'content' field is required in the request body."},
            )
        lang_code = detectlanguagebycomprehend(str(text))
        return PlainTextResponse(content=lang_code, media_type="text/plain") 
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error" :f"Invalid request body. {str(e)}"}
        )
        

@app.get("/checkUserDetails")
async def check_user_details(call_sid: str = Query(...)):
    print("Check User Details Called")
    try:
        call = twilio_client.calls(call_sid).fetch()
        # from_phone_number = call._from   # Caller phone number
        print(len(call.to))
        if call.to == "+18784255139": # Outgoing Calls
            phone_number = call._from # Reciever Number
        else : phone_number = call.to 

        # Validate phone number input
        if not phone_number or not isinstance(phone_number, str):
            return JSONResponse(status_code=400, content={"error": "Invalid phone number. It must be a string."})

        user_details = fetch_user_details(phone_number)
        print( "User details ", user_details)
        if not user_details:
            return JSONResponse(status_code=404, content={"error": "User not found."})

        return JSONResponse(status_code=200, content=user_details)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})




@app.get("/ping")
async def ping(request : Request):
	return JSONResponse(content = {"status":"Pinged !"})


@app.get("/call")
async def voice(no:str ):
    """Respond to incoming phone calls with a menu of options"""
    # Start our TwiML response
    FROM_NUMBER = f"{no}" 
    # FROM_NUMBER = "+916302208769"
    # 

    APP_NUMBER = "+18784255139" #"+18647408060"#"+19125518907" #"" #"+"+18784255139" #"  # My Twilio Phone Number 
    await asyncio.sleep(1)
	## Need to change the ngrok link ##
    resp = f"""
 <Response>
    <Connect>
      <Stream url="wss://content-wired-halibut.ngrok-free.app/connection" /> 
    </Connect>
  </Response>
    """

    call = twilio_client.calls.create(
        twiml=resp,
        to=FROM_NUMBER,
        from_=APP_NUMBER,
    )


if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)