require("colors");
const { BedrockRuntimeClient, InvokeModelCommand } = require("@aws-sdk/client-bedrock-runtime");
const EventEmitter = require("events");
const tools = require("../functions/function-manifest");

const availableFunctions = {};
tools.forEach((tool) => {
  let functionName = tool.function.name;
  availableFunctions[functionName] = require(`../functions/${functionName}`);
});

class GptService extends EventEmitter {
  constructor(config) {
    super();
    this.client = new BedrockRuntimeClient(config); // Initialize Bedrock client with config
    this.userContext = [];
    this.sharedContext = []; // Shared context for both functions
    this.partialResponseIndex = 0;
  }

  setCallSid(callSid) {
    // this.userContext.push({ role: "system", content: `callSid: ${callSid}` });
  }
  

  validateFunctionArgs(args) {
    try {
      return JSON.parse(args);
    } catch (error) {
      console.log("Warning: Double function arguments returned by Bedrock:", args);
      if (args.indexOf("{") != args.lastIndexOf("{")) {
        return JSON.parse(
          args.substring(args.indexOf("{"), args.indexOf("}") + 1)
        );
      }
    }
  }

  updateUserContext(name, role, text) {
    if (name !== "user") {
      this.userContext.push({ role: role, name: name, content: text });
      this.sharedContext.push({ role: role, name: name, content: text });
    } else {
      this.userContext.push({ role: role, content: text });
      this.sharedContext.push({ role: role, content: text });
    }
  }

  async completion(sid, text, interactionCount,language, role = "user", name = "user") {
    this.updateUserContext(name, role, text);
    console.time("Bedrock Answer generation Time : ".yellow)
    const api_url = "http://98.82.75.144:8000/generate";
    // Prepare input for Bedrock API
    const payload = JSON.stringify({ content: this.userContext ,callSid: sid , interactionCount : interactionCount, language: language});
    // console.time("Bedrock Answer generation Time : ".yellow)
    // console.log("==> Generate payload ==>", payload)
    const response = await fetch(api_url, {
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
      completeResponse += partialResponse; // Fix variable name
      const gptReply = {
        partialResponseIndex: this.partialResponseIndex,
        partialResponse,
      };
      console.log("--------------------------------");
      console.log("Saying : ", partialResponse);
      console.log("--------------------------------");
      this.emit("gptreply", gptReply, interactionCount);
      this.partialResponseIndex++;
      partialResponse = "";
    }
    this.userContext.push({'role': 'assistant', 'content': completeResponse});
    this.sharedContext.push({'role': 'assistant', 'content': completeResponse});
    console.log("Complete Response ", completeResponse);
    // console.log("userContext", this.userContext);
    console.log("sharedContext updated, length:", this.sharedContext.length);
    console.timeEnd("Bedrock Answer generation Time : ".yellow)
    
    // Store the context in global variable for access across instances
    global.conversationContext = [...this.sharedContext];
    return this.sharedContext; // Return context for use outside
  }

  async judge_sms_email(sid, providedContext = null) {
    // Determine which context to use
    let contextToUse = providedContext;
    
    // Try different sources for context in order of preference
    if (!contextToUse || contextToUse.length === 0) {
      if (this.sharedContext && this.sharedContext.length > 0) {
        contextToUse = this.sharedContext;
        console.log("Using instance sharedContext, length:", this.sharedContext.length);
      } else if (this.userContext && this.userContext.length > 0) {
        contextToUse = this.userContext;
        console.log("Using instance userContext, length:", this.userContext.length);
      } else if (global.conversationContext && global.conversationContext.length > 0) {
        contextToUse = global.conversationContext;
        console.log("Using global conversationContext, length:", global.conversationContext.length);
      } else {
        console.log("WARNING: No conversation context found for judgment");
        contextToUse = [];
      }
    }
    
    const api_url = "http://98.82.75.144:8000/judge_sms_email";
    const payload = JSON.stringify({ 
      content: contextToUse,
      callSid: sid
    });
    console.log("+==+ PAYLOAD FOR JUDGING MAIL/SMS +==+", payload)
    // console.log("Context being sent:", JSON.stringify(contextToUse));
    const response = await fetch(api_url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: payload,
    });
    console.log("SMS Email judging response ::: ")
  }
}
module.exports = { GptService };