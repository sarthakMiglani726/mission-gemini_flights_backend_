import vertexai
import streamlit as st
from vertexai.preview import generative_models
from vertexai.preview.generative_models import GenerativeModel, Tool, Part, Content, ChatSession
from flight_manager import search_flights

project = "sample-gemini"
vertexai.init(project = project)

# Define Tool
get_search_flights = generative_models.FunctionDeclaration(
    name="get_search_flights",
    description="Function to search for flights",
    parameters={
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "The airport or city code for the departure location"
            },
            "destination": {
                "type": "string",
                "description": "The airport or city code for the arrival location"
            },
            "departure_date": {
                "type": "string",
                "format": "date",
                "description": "The departure date in YYYY-MM-DD format"
            },
            "return_date": {
                "type": "string",
                "format": "date",
                "description": "The return date in YYYY-MM-DD format"
            },
            "passengers": {
                "type": "integer",
                "description": "The number of passengers"
            },
            "class": {
                "type": "string",
                "description": "The class of service (e.g., economy, business, first)"
            }
        },
        "required": ["origin", "destination", "departure_date"]
    }
)

book_flight_declaration = generative_models.FunctionDeclaration(
    name="book_flight",
    description="Books a flight with the given flight ID, seat type, and number of seats.",
    parameters={
        "type": "object",
        "properties": {
            "flight_id": {
                "type": "integer",
                "description": "The ID of the flight to book."
            },
            "seat_type": {
                "type": "string",
                "description": "The type of seat to book (e.g., 'economy', 'business')."
            },
            "num_seats": {
                "type": "integer",
                "description": "The number of seats to book.",
                "default": 1
            }
        },
        "required": ["flight_id", "seat_type"]
    }
)

# Define tool and model with tools
tools = generative_models.Tool(
    function_declarations=[get_search_flights, book_flight_declaration],
)

config = generative_models.GenerationConfig(temperature=0.4)
# Load model with config
model = GenerativeModel(
    "gemini-pro",
    tools = [tools],
    generation_config = config
)

# helper function to unpack responses
def handle_response(response):
    
    # Check for function call with intermediate step, always return response
    if response.candidates[0].content.parts[0].function_call.args:
        # Function call exists, unpack and load into a function
        response_args = response.candidates[0].content.parts[0].function_call.args
        
        function_params = {}
        for key in response_args:
            value = response_args[key]
            function_params[key] = value
        
        results = search_flights(**function_params)
        
        if results:
            intermediate_response = chat.send_message(
                Part.from_function_response(
                    name="get_search_flights",
                    response = results
                )
            )
            
            return intermediate_response.candidates[0].content.parts[0].text
        else:
            return "Search Failed"
    else:
        # Return just text
        return response.candidates[0].content.parts[0].text

# helper function to display and send streamlit messages
def llm_function(chat: ChatSession, query):
    response = chat.send_message(query)
    output = handle_response(response)
    
    with st.chat_message("model"):
        st.markdown(output)
    
    st.session_state.messages.append(
        {
            "role": "user",
            "content": query
        }
    )
    st.session_state.messages.append(
        {
            "role": "model",
            "content": output
        }
    )

st.title("Gemini Flights")

chat = model.start_chat()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display and load to chat history
for index, message in enumerate(st.session_state.messages):
    content = Content(
            role = message["role"],
            parts = [ Part.from_text(message["content"]) ]
        )
    
    if index != 0:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    chat.history.append(content)

# For Initial message startup
if len(st.session_state.messages) == 0:
    # Invoke initial message
    initial_prompt = "Introduce yourself as a flights management assistant, ReX, powered by Google Gemini and designed to search/book flights. You use emojis to be interactive. For reference, the year for dates is 2024"

    llm_function(chat, initial_prompt)

# For capture user input
query = st.chat_input("Gemini Flights")

if query:
    with st.chat_message("user"):
        st.markdown(query)
    llm_function(chat, query)
