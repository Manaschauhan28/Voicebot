# Voice-Based Call Center POC 

## Project Overview
The Proof of Concept (POC) aimed to design a voice-based call center for handling FAQs and assisting users in performing service requests. This solution leverages advanced AI and speech recognition technologies to provide a seamless, automated customer service experience.

## Project Structure
```
├── node_app/                    		# Node.js backend service
│   ├── services/               		# Core service implementations
│   │   ├── gpt-service.js      		# GPT integration service
│   │   └── transcription-service.js  	# Speech-to-text service
│   │   └── tts-service.js  		  	# text-to-speech service
│   │   └── stream-service.js  		  	# audio streaming service
│   ├── functions/              		# Function definitions
│   ├── audio/                  		# Audio processing utilities
│   └── app.js                  		# Main application entry point
│   └── Dockerfile                  	# Dockerfile for this node based server
│
├── python_app/                 # Python backend service
│   ├── app.py                  # Main application logic
│   ├── utils.py                # Utility functions
│   ├── faq_prompt.txt          # FAQ handling prompts
│   └── prompt.txt              # General conversation prompts
│   └── requirements.txt        # Dependencies document for python
│   └── Dockerfile              # Dockerfile for this python based server

```

## Services Used
1. **Speech Recognition**
   - Deepgram for real-time speech-to-text conversion
   - Supports multiple languages
   - Real-time transcription with punctuation

2. **Natural Language Processing**
   - GPT-based conversation handling
   - Context-aware responses
   - Multi-turn conversation support

3. **Voice Processing**
   - MULAW/8000 audio stream processing
   - Real-time audio streaming
   - Endpointing and utterance detection

## Offered Solution
The solution provides:
1. **Automated Customer Service**
   - 24/7 availability
   - Instant responses to customer queries
   - Consistent service quality

2. **Service Request Handling**
   - Policy document requests
   - Insurance card copies
   - Coverage proof letters
   - Quote copies
   - Loss payee form processing
   - Mortgagee form processing
   - Claim assistance

3. **Multi-Modal Communication**
   - Voice-based interaction
   - Email follow-up capability
   - SMS notification support

## Discovery & Requirement Analysis
1. **Customer Needs**
   - Quick access to insurance information
   - Easy document requests
   - Multilingual support
   - 24/7 availability

2. **Business Requirements**
   - Reduced call center costs
   - Improved customer satisfaction
   - Automated service request processing
   - Scalable solution

3. **Technical Requirements**
   - Real-time speech processing
   - Accurate transcription
   - Natural conversation flow
   - Secure data handling

## Challenges
1. **Technical Challenges**
   - Real-time audio processing latency
   - Accurate speech recognition in noisy environments
   - Maintaining conversation context
   - Handling multiple languages

2. **Integration Challenges**
   - Synchronizing multiple services
   - Managing state across services
   - Handling service failures gracefully

3. **User Experience Challenges**
   - Natural conversation flow
   - Accurate intent recognition
   - Proper handling of edge cases

## Proof of Concepts
1. **Speech Recognition POC**
   - Implemented Deepgram integration
   - Achieved real-time transcription
   - Added language detection

2. **Conversation Flow POC**
   - Implemented GPT-based responses
   - Added context management
   - Achieved natural conversation handling

3. **Service Request POC**
   - Implemented request identification
   - Added delivery mode detection
   - Created automated response system

## Solution & Implementations
1. **Architecture**
   - Microservices-based design
   - Event-driven communication
   - Scalable container deployment

2. **Key Features**
   - Real-time speech processing
   - Context-aware responses
   - Multi-language support
   - Automated service requests
   - Multi-modal communication

3. **Technical Implementation**
   - Node.js for real-time processing
   - Python for AI/ML processing
   - Docker for containerization
   - Event-driven architecture

4. **Security & Compliance**
   - Secure audio processing
   - Data privacy protection
   - Compliance with insurance regulations

## Getting Started
1. Clone the repository
2. Set up environment variables
3. Install dependencies
4. Run the services using Docker Compose

## Environment Variables
Create a .env file inside the node_app/ folder and include the following keys:
```
DEEPGRAM_API_KEY=your_deepgram_key
SERVER_URL=your_backend_server_url
XI_API_KEY=your_xi_api_key
VOICE_ID=your_elevenlabs_voice_id
XI_MODEL_ID=your_xi_model_id
```
Ensure that your Node.js app running on port 3000 is exposed to the internet. You can use:

- Ngrok for quick development purposes, or

- Docker container networking with a public-facing server for production.

Configure the exposed URL as the webhook on the Twilio phone number settings in the Twilio Console.

## Contributing
Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details. 
