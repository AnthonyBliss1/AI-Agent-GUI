# AI Agent GUI
This project is a very simple Python GUI wrapped around a Langchain Pandas Dataframe Agent and Flowise APIs. With the Pandas DF Agent we use natural language to talk to Pandas dataframes. Through Flowise, we can create RAG Chatbots to interact with documents or even webpages. The script is meant to be configurable so any user can utilize these powerful tools.

# Setup

## Open AI 
Navigate to Openai.com > API > API Keys > create new secret key. Copy this key and paste it into the .env file next to "OPENAI_API_KEY". You will be prompted to update the .env file before running the .py file. 

## Flowise
This script utilizes 4 Flowise Chatflows; PDF Upsert, DOCX Upsert, WEB Upsert, and Load. You will need to setup each of these components before interacting with the chat widgets. Please follow the documentation to setup Flowise [here](https://docs.flowiseai.com/getting-started). You can run Flowise locally or deploy on Render, Railway, AWS etc. but running locally is the best way to get started fast and for free. Once you have Flowise installed, download each of the flow files from this repository's "flows" folder and upload them to Flowise by clicking "Add New" > "Load Chatflow". Now, you will need to configure each flow with your OpenAI and Pinecone credentials. 

> *At this point, if you do not have a Pinecone account, navigate [here](https://www.pinecone.io/) to create an account and setup a free Starter Index. **Make sure to set the index dimensions as 1536*** 

In Flowise, you can also tweak each node in the flow for more specific use cases or to improve outputs i.e. change LLM model, change embedding model, text splitter config, or adjusting prompts.

> [!IMPORTANT]
> -Only for your PDF, DOCX, and WEB Upsert flows, click the green upsert button in Flowise (on the right side), select Python, and copy the API URL. 
>  - If you are running Flowise locally, your Upsert URL should look something like this : http://localhost:3000/api/v1/vector/upsert/your-chatflow-ID. To use these API's, run the script, click "Flowise" in the toolbar and paste your URLs in the correct sections.
> -For your Load/Predict URL, simply click the "</>" icon in Flowise while looking at the flow, select Python, and copy the API URL.
>  - Your Load/Predict URL should look something like this: http://localhost:3000/api/v1/prediction/your-chatflow-ID.

To explain, the script has 3 upsert flows; PDF, DOCX, WEB. These calls will upsert your specific document types into your Pinecone index. The Load flow will be required to actually send queries and receive responses (Q&A). We have a load flow so we do not need to store an additional Predict URL for each one of our Upsert flows.

## Pinecone
After you have Flowise and your flows set up, you should have already set up a Pinecone account and index. Again, a **free** Starter Index will work perfect for this script. While the script is running, click "Pinecone" in the toolbar of the GUI and paste in your Pinecone API Key and index name. Even though your flows are already set up with your Pinecone credentials, this script runs a "delete_all_records" function on close to clear all records from the namespaces created in your Pinecone index. This will make sure you don't go over the 100 namespace limit for the starter index. 

> [!NOTE]
> The Pinecone Starter Index is hosted in the us-central-1 (Iowa) region of the GCP cloud. If your location is far enough, there may be some latency after upsert confimation from the script before your Load flow will be able search the namespace. You can upgrade to an S1 pod for better performance. More information on indexes can be found [here](https://docs.pinecone.io/guides/indexes/understanding-indexes). More information on index limits can be found [here](https://docs.pinecone.io/reference/limits#retention)

## Have Fun!

This project was created to help introduce AI tools to new users. Hopefully this script is easy to get up and running, have fun!
