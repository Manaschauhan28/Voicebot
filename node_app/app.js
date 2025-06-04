require("dotenv").config();
require("colors");
const express = require("express");
const path = require("path");
const ExpressWs = require("express-ws");
const fs = require("fs");
const { WaveFile } = require("wavefile");
const { GptService } = require("./services/gpt-service");
const { StreamService } = require("./services/stream-service");
const { TranscriptionService } = require("./services/transcription-service");
const { SpanishTranscriptionService } = require("./services/spanish-transcription-service");
const { EnglishTranscriptionService } = require("./services/english-transcription-service");
const { TextToSpeechService } = require("./services/tts-service");
const { dir } = require("console");

const app = express();
ExpressWs(app);

const PORT = process.env.PORT || 3000;

app.post("/incoming", (req, res) => {
  res.status(200);
  res.type("text/xml");
  res.end(`
  <Response>
    <Connect>
      <Stream url="wss://${process.env.SERVER}/connection" />
    </Connect>
  </Response>
  `);
 
});


// Define thinking phrases with consistent file formats and durations
const THINKING_PHRASES = {
  default: [
    { file: "typing-1.mp3", duration: 7500 },
    { file: "mouse-click.mp3", duration: 6000 }
  ],
  es: [
    { file: "please_wait_spanish_liz.mp3", duration: 6000 },
    { file: "perminte_un_momento.mp3", duration: 6000 },
    { file: "one_second_spanish_lizy.mp3", duration: 6000 }
  ],
  en: [
    { file: "allow_me_amoment_please.mp3", duration: 6000 },
    { file: "just_a_moment.mp3", duration: 6000 },
    { file: "hmm_just_a_second.mp3", duration: 6000 },
    { file: "let_me_check_that_for_you.mp3", duration: 6000 }
  ]
};



app.ws("/connection", (ws) => {
  console.log("RECEIVED");
  // console.time('execution time ')
  ws.on("error", console.error);
  // Filled in from start message

  let finalDetectedLanguage = null;
  let languageDetectionComplete = false; // Flag to track if language detection is complete
  let streamSid;
  let callSid;
  
  
  const gptService = new GptService();
  const streamService = new StreamService(ws);
  let transcriptionService = new TranscriptionService();  // Initial multi-language service
  let spanishTranscriptionService = null;  // Initialize as null
  let englishTranscriptionService = null;  // Initialize as null
  const ttsService = new TextToSpeechService({});
  console.log("I'm Here ...")	
  let marks = []; 
  let interactionCount = 0;
  let wasTrueBefore = false;
  let mp3FilePath = "";
  
  // Function to switch transcription service based on detected language
  const switchTranscriptionService = (language) => {
    if (languageDetectionComplete) return;
    
    console.log(`Switching transcription service to ${language}... ${typeof(language)}`.yellow);
    
    // Store the current service to close it after setting up the new one
    const currentService = transcriptionService;
    
    // Initialize the appropriate service based on language
    if (language == 'es') {
      spanishTranscriptionService = new SpanishTranscriptionService();
      transcriptionService = spanishTranscriptionService;
      finalDetectedLanguage = "es";   
      console.log("Using Spanish transcription service".green);
    } else if (language == 'en') {
      englishTranscriptionService = new EnglishTranscriptionService();
      transcriptionService = englishTranscriptionService; 
      finalDetectedLanguage = "en";
      console.log("Using English transcription service".green);
    } else {
      // For any other language, use the appropriate service based on the language
      transcriptionService = new TranscriptionService();
      finalDetectedLanguage = language;
      console.log(`Using default transcription service for language: ${language}`.green);
    }
    
    // Set up event listeners for the new transcription service
    setupTranscriptionServiceListeners();
    
    // Close all other services
    if (currentService) {
      console.log("Closing multi-language service".yellow);
      currentService.closeDeepgram();
    }
    
    // Close unused services
    if (language != 'es' && spanishTranscriptionService) {
      console.log("Closing Spanish service".yellow);
      spanishTranscriptionService.closeDeepgram();
    }
    if (language != 'en' && englishTranscriptionService) {
      console.log("Closing English service".yellow);
      englishTranscriptionService.closeDeepgram();
    }
    
    // Mark language detection as complete
    languageDetectionComplete = true;
    console.log(`Transcription Service Switching Completed. Active language: ${finalDetectedLanguage}`.yellow);
  };

  // Function to set up event listeners for the transcription service
  const setupTranscriptionServiceListeners = () => {
    // Set up utterance listener
    transcriptionService.on("utterance", async (text) => {
      // This is a bit of a hack to filter out empty utterances
      if (marks.length > 0 && text?.length > 5) {
        console.log("Twilio -> Interruption, Clearing stream".red);
        ws.send(
          JSON.stringify({
            streamSid, 
            event: "clear",
          }),
        );
      }
    });

    // Set up transcription listener
    transcriptionService.on("transcription", async (text) => {
      console.time("Transcription time".yellow)
      if (!text) {
        return;
      }
      trans.push(text.toLowerCase());
      
      try {
        gptService.completion(callSid, text, interactionCount, finalDetectedLanguage);
        const thinkingPhrases = THINKING_PHRASES[finalDetectedLanguage] || THINKING_PHRASES.default;
        const selectedPhrase = thinkingPhrases[Math.floor(Math.random() * thinkingPhrases.length)];
        mp3FilePath = path.join(__dirname, "audio", selectedPhrase.file);
        streamService.think(mp3FilePath);
      } catch (error) {
        console.error("Error in transcription handling:", error);
      }

      // Detect language and switch service if needed
      if (interactionCount === 0) {
        finalDetectedLanguage = await detectLanguage(text);
      } else if (interactionCount === 1) {
        switchTranscriptionService(finalDetectedLanguage);
      }
      
      interactionCount += 1;
    });
  };
  
  // Set up initial transcription service listeners
  setupTranscriptionServiceListeners();
  
  // Incoming from MediaStream
  ws.on("message", function message(data) {
    const msg = JSON.parse(data);
    if (msg.event === "start") {
      streamSid = msg.start.streamSid;
      callSid = msg.start.callSid;
      streamService.setStreamSid(streamSid);
      gptService.setCallSid(callSid);
      const filepath = path.join(__dirname, "audio","initial_introduction_updated_1.wav");
      // const user_verification = gptService.checkUserdetails(callSid);
      const wavData = fs.readFileSync(filepath);
      let wav = new WaveFile(wavData);
      wav.toSampleRate(8000);
      wav.toMuLaw();
      // Read WAV file
      // Extract only the raw µ-law audio data, excluding headers
      const rawMuLawData = wav.data.samples;

        let base64Chunk = Buffer.from(rawMuLawData).toString("base64");
        streamService.sendAudio(base64Chunk);
      console.log(
        `Twilio -> Starting Media Stream for ${streamSid}`.underline.red,
      );
      
    } else if (msg.event === "playAudio") {
      transcriptionService.send(msg.media.payload, callSid); 
    } else if (msg.event === "media") {
      transcriptionService.send(msg.media.payload, callSid);
    } else if (msg.event === "mark") {
      const label = msg.mark.name;
      console.log(
        `Twilio -> Audio completed mark (${msg.sequenceNumber}): ${label}`.red,
      );
      marks = marks.filter((m) => m !== msg.mark.name);
    } else if (msg.event === "stop") {
      console.log(`Twilio -> Media stream ${streamSid} ended.`.underline.red);
    }
  });
  
let trans = [];

// Function for Judging Ending
async function containsGoodbye(user_sentences) {
  // console.log("Words List :- ", user_sentences);
  end_api_url = "http://98.82.75.144:8000/judge_ending";
   const payload = JSON.stringify({content: user_sentences.slice(-2).join(" , ")});
    // console.time("Bedrock Answer generation Time : ".yellow)
	console.log("==> Judge Endingpayload ==>", payload);
    const response = await fetch(end_api_url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: payload,
    });
    let stream = response.body.getReader();
    let completeResponse = "";
  
    while (true) {
      const { done, value } = await stream.read();
      if (done) break;
      let partialResponse = new TextDecoder().decode(value);
      completeResponse += partialResponse;
    }

    // console.log("Complete Response : ".green, completeResponse)
    let jsonStart = completeResponse.indexOf("{");
    let jsonEnd = completeResponse.indexOf("}", jsonStart) + 1; 

    // Check if a valid JSON part exists
    if (jsonStart !== -1) {
        let jsonPart = completeResponse.substring(jsonStart, jsonEnd);
        
        try {
            let parsedResponse = JSON.parse(jsonPart);
            return (parsedResponse.output === 1 || String(parsedResponse.output) === '1'  &&
            parsedResponse.confidence && parsedResponse.confidence.toLowerCase() === 'high'); 
        } catch (error) {
            return false;
        }
    } else {
       return false;
    }
    
    // return completeResponse.split(" ").includes("1");
    
}


// Function for detecting language 
async function detectLanguage(text) {
  api_url = "http://98.82.75.144:8000/detectlanguage";
  const payload = JSON.stringify({content: text});
    // console.time("Bedrock Answer generation Time : ".yellow)
	// console.log("==> payload ==>", payload)
  try {
    const response = await fetch(api_url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: payload,
    });

    if (!response.ok) {
      const errorMessage = await response.text();
      throw new Error(`HTTP error! Status: ${response.status} - ${errorMessage}`);
    }

    // Read the response as text (not a ReadableStream)
    const lang_code = await response.text();
    return lang_code.trim(); // Trim whitespace just in case
  } catch (error) {
    console.error("Error detecting language:", error);
    return null;
  }
}



  gptService.on("gptreply", async (gptReply, icount) => {
    if (!gptReply) {
      return;
    }
    console.log(gptReply.partialResponse)
    console.log("**************************************")
    console.log(
      `Interaction ${icount}: GPT -> TTS: ${gptReply.partialResponse}`.green,
    );
    
  console.log("\n\nSending for Detection ", gptReply)  
  const language = await detectLanguage(gptReply)  // Detecting response language
  ttsService.generate(gptReply, icount, language);
  const result = await containsGoodbye(trans)
  console.log("Ending Result : ", result)
  
    if (result || wasTrueBefore) { 
      console.log("mp3 file path Fetched ::", mp3FilePath)
      try {
        if (mp3FilePath.trim() === "/node_app/audio/typing-1.mp3") {
          console.log("\n Sleep Time : 10.5 sec");
          await new Promise(resolve => setTimeout(resolve, 10500));
        } else {
          console.log("\n Sleep Time : 7.0 sec");
          await new Promise(resolve => setTimeout(resolve, 7000));
        }
        
        // After sleep, close the transcription service
        transcriptionService.closeDeepgram();
      } catch (error) {
        console.error("Error during sleep:", error);
      }
    }
    wasTrueBefore = result;
  });
  
  ttsService.on("speech", (responseIndex, audio, label, icount) => {
    console.log(`Interaction ${icount}: TTS -> TWILIO: ${label}`.blue);
    console.time("Sending Time : ".white)
    streamService.buffer(responseIndex, audio);
    console.timeEnd("Sending Time : ".white)
  });

  streamService.on("audiosent", (markLabel) => {
    marks.push(markLabel);
  });
});


app.listen(PORT);
console.log(`Server running on port ${PORT}`);