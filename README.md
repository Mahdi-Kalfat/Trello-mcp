steps to install the llm agent :

    - create virtual env :
        python -m venv venv
        .\venv\Scripts\activate

    - Install packages :
        pip install langchain langchain-community langchain-core langchain-openai requests
    
    - pull ollama :
        ollama pull llama3
    
    - Start ollama : 
        ollama serve