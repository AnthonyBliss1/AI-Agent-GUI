# Setup

## Open AI 
Navigate to Openai.com > API > API Keys > create new secret key. Copy this key and paste it into the .env file next to "OPENAI_API_KEY". You will be prompted to update the .env file before running the .py file. 

## Flowise
This script utilizes 4 Flowise Chatflows; PDF Upsert, DOCX Upsert, WEB Upsert, and Load. You will need to setup each of these components before interacting with the chat widgets. Please follow documentation to setup Flowise here. You can run Flowise locally or deploy on Render, Railway, AWS etc. but running locally is the best way to get started fast. Once you have Flowise installed, download each of the flow files from this repository and upload them to your Flowise. You will need to configure each flow with your OpenAI and Pinecone credentials. You can also tweak each node in the flow for more specific use cases. **THE MOST IMPORTANT PART** for your PDF, DOCX, and WEB Upsert flows, click the green upsert button in Flowise (on the right side), select Python, and copy the upsert API call. If you are running locally, it should look something like this : http://localhost:3000/api/v1/vector/upsert/your-chatflow-ID. To use these API's, run the application, click "Flowise" in the toolbar and paste in your URLs. **ONLY FOR THE LOAD FLOW** Simply click the "</>" icon in Flowise while looking at your flow, and copy that URL for Python. 

To explain, the script has 3 upsert API calls; PDF, DOCX, WEB. These calls will upsert your specific document types into your Pinecone index. The Load flow will be required to actually send queries and receive responses. We have the load flow so we do not need to store an additional Predict URL for each of our Upsert flows.

## Pinecone
After you have Flowise and your flows set up, you should have already set up a Pinecone account and index. Again, a **free** Starter index will work perfect for this script. While the script is running, click "Pinecone" in the toolbar and paste in your Pinecone API Key and index name. Even though your flows are already set up to use Pinecone, this script runs a "delete_all_records" function on close to clear all records from the namespace created in your Pinecone index. This will make sure you don't go over the limit on the starter index.

## Have Fun!

This project was created to help introduce AI tools to new users. Hopefully this script is easy to get up and running, have fun!
