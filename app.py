import streamlit as st
import requests
import uuid
import json
from deep_translator import GoogleTranslator
from config import WEBHOOK_URL, AUTH_HEADER

st.set_page_config(page_title="Web Agent Interface", page_icon="🤖", initial_sidebar_state="collapsed")

# Initialize session data
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"  # You can modify this as needed
if "messages" not in st.session_state:
    st.session_state.messages = []

def translate_text(text):
    try:
        translator = GoogleTranslator(source='en', target='pt')
        # Translate in chunks to handle long texts
        max_chunk = 4500  # Google Translate limit
        if len(text) > max_chunk:
            chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
            translated = ''
            for chunk in chunks:
                translated += translator.translate(chunk) + ' '
            return translated.strip()
        return translator.translate(text)
    except Exception as e:
        st.sidebar.error(f"Translation error: {str(e)}")
        return text

def is_portuguese(text):
    """Check if text is likely Portuguese based on common words"""
    pt_indicators = ['da', 'dos', 'das', 'em', 'para', 'com', 'na', 'no', 'aos']
    words = text.lower().split()
    return any(word in pt_indicators for word in words)

def is_portuguese_title(text):
    """Enhanced Portuguese detection for titles"""
    pt_indicators = [
        'da', 'dos', 'das', 'em', 'para', 'com', 'na', 'no', 'aos',
        'geração', 'viver', 'compra', 'novo', 'secretária', 'estado',
        'apoios', 'habitação', 'falhada'
    ]
    words = text.lower().split()
    return any(word in pt_indicators for word in words)

def format_article_with_date(title, date=None):
    """Format article title with date if available"""
    if date:
        return f"{title.strip()} (Publicado em: {date})"
    return title.strip()

def clean_markdown(text):
    # Initial JSON cleanup
    if isinstance(text, str):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) > 0:
                text = parsed[0].get('output', '')
        except:
            pass
    
    # Remove escape characters
    text = text.replace('\\n', '\n')
    text = text.replace('\\r', '\r')
    text = text.replace('\\"', '"')
    text = text.replace('\\t', '\t')
    
    # Split into sections for targeted translation
    sections = text.split('\n\n')
    formatted_sections = []
    current_date = "13 de fevereiro de 2025"  # Default date if needed
    in_article_section = False
    
    for section in sections:
        if not section.strip():
            continue
        
        # Handle main sections
        if section.startswith('#') or section.startswith('Notícias'):
            formatted_sections.append(section)
            in_article_section = True
            continue
            
        # Handle article entries
        if in_article_section and any(marker in section for marker in ['Geração Z', 'Viver no', 'Compra', 'Novo Hub', 'Apoio à']):
            # Format article with date
            formatted_sections.append(format_article_with_date(section, current_date))
        elif 'Leia mais' in section:
            formatted_sections.append(section)
        else:
            # Add other sections as is
            formatted_sections.append(section)
    
    # Process Outros Tópicos section
    outros_topicos_index = -1
    for i, section in enumerate(formatted_sections):
        if 'Outros Tópicos' in section:
            outros_topicos_index = i
            break
    
    if outros_topicos_index >= 0:
        # Add dates to items in Outros Tópicos if they don't have them
        topics = formatted_sections[outros_topicos_index].split('\n')
        formatted_topics = [topics[0]]  # Keep the header
        for topic in topics[1:]:
            if topic.strip() and not any(date_marker in topic for date_marker in ['Publicado em:', '(Data:']):
                formatted_topics.append(format_article_with_date(topic, current_date))
            else:
                formatted_topics.append(topic)
        formatted_sections[outros_topicos_index] = '\n'.join(formatted_topics)
    
    return '\n\n'.join(formatted_sections).strip()

def send_to_webhook(url):
    headers = {
        "Authorization": AUTH_HEADER,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "query": url,
        "user_id": st.session_state.user_id,
        "request_id": str(uuid.uuid4()),
        "session_id": st.session_state.session_id
    }
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers=headers
        )
        
        # Parse JSON response
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            # Get the markdown content and clean it
            content = data[0].get('output', '')
            # Convert to JSON string and back to handle escape sequences
            content = json.loads(json.dumps(content))
            return content.strip()
            
        return "No content received"
        
    except Exception as e:
        return f"Error: {str(e)}"

# Add CSS to hide sidebar completely
st.markdown("""
    <style>
        [data-testid="collapsedControl"] {display: none;}
        section[data-testid="stSidebar"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.title("Web Agent Interface 🤖")

# Initialize chat input state
if "url_processed" not in st.session_state:
    st.session_state.url_processed = False

# Display chat history with markdown support
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# Replace the URL input section with:
if not st.session_state.url_processed:
    url = st.text_input("Enter URL:", placeholder="https://example.com")
    process_button = st.button("Process URL")
    
    if url and process_button:
        with st.spinner('Processing URL...'):  # This will show next to the input
            # Display URL as a user message
            st.session_state.messages.append({"role": "user", "content": f"🔗 {url}"})
            with st.chat_message("user"):
                st.markdown(f"🔗 {url}")
            response = send_to_webhook(url)
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.url_processed = True
            st.rerun()
else:
    # Show chat input for follow-up questions
    if prompt := st.chat_input("Ask a follow-up question..."):
        with st.spinner('Processing question...'):  # This will show next to the chat input
            # Display user's question immediately
            st.session_state.messages.append({"role": "user", "content": f"❓ {prompt}"})
            with st.chat_message("user"):
                st.markdown(f"❓ {prompt}")
            
            # Get and display assistant's response
            response = send_to_webhook(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
            st.rerun()
