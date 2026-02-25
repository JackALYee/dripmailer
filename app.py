import streamlit as st
import pandas as pd
import smtplib
import time
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid

# --- PAGE CONFIG ---
st.set_page_config(page_title="Drip Mailer", page_icon="📧", layout="wide")

# --- CUSTOM CSS (Aurora Tech Flow) ---
st.markdown("""
<style>
    .stApp {
        background-color: #050810;
        background-image: radial-gradient(circle at 50% -20%, #0B1221, #050810);
        color: #A0AEC0;
    }
    h1, h2, h3 { color: #FFFFFF !important; }
    .stButton>button {
        background: linear-gradient(135deg, #2AF598, #009EFD);
        color: #050810;
        font-weight: 600;
        border: none;
        box-shadow: 0 0 15px rgba(0, 158, 253, 0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 25px rgba(42, 245, 152, 0.6);
        border: none;
        color: #050810;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(255, 255, 255, 0.05);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #2AF598;
        box-shadow: 0 0 0 1px #2AF598;
    }
    .aurora-text {
        background: linear-gradient(to right, #2AF598, #009EFD);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- DEFAULTS & TEMPLATES ---
DEFAULT_BODY = """Hi {first_name},

I hope this email finds you well. I noticed that {company} is doing some incredible work lately.

As someone working as a {role}, I thought you might be interested in how our new tools can help streamline your daily operations. We've helped similar teams increase their efficiency by over 20%.

Would you be open to a brief 10-minute chat next week?

Best regards,"""

DISCLAIMER_HTML = """
<div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-family: Arial, sans-serif; font-size: 10px; color: #64748b; line-height: 1.4; text-align: justify;">
    <strong>Email Disclaimer:</strong> This e-mail is intended only for the person or entity to which it is addressed and may contain confidential and/or privileged material. Any review, retransmission, dissemination or other use of, or taking of any action in reliance upon, the information in this e-mail by persons or entities other than the intended recipient is prohibited and may be unlawful. If you received this e-mail in error, please contact the sender and delete it from any computer.
</div>
"""

def get_signature_html(sig_id, data):
    if sig_id == "Minimalist Professional":
        return f"""
        <div style="font-family: Arial, sans-serif; color: #333; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">
            <p style="margin: 0; font-weight: bold; font-size: 14px;">{data['name']}</p>
            <p style="margin: 0; font-size: 12px; color: #666;">{data['title']} | {data['company']}</p>
            <p style="margin: 0; font-size: 12px; color: #0066cc;">{data['email']} | {data['phone']}</p>
        </div>
        {DISCLAIMER_HTML}
        """
    elif sig_id == "Creative with Avatar":
        return f"""
        <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin-top: 20px; display: flex; align-items: center; gap: 15px;">
            <img src="{data['avatarUrl']}" alt="Avatar" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #e2e8f0;" />
            <div>
                <p style="margin: 0; font-weight: 600; font-size: 15px; color: #1e293b;">{data['name']}</p>
                <p style="margin: 2px 0; font-size: 13px; color: #64748b;">{data['title']}</p>
                <p style="margin: 2px 0; font-size: 13px; color: #3b82f6;">{data['email']} <span style="color: #94a3b8;">|</span> <span style="color: #64748b;">{data['phone']}</span></p>
                <a href="{data['website']}" style="margin: 0; font-size: 13px; color: #3b82f6; text-decoration: none;">{data['website'].replace('https://', '')}</a>
            </div>
        </div>
        {DISCLAIMER_HTML}
        """
    else: # Corporate with Logo
        return f"""
        <div style="font-family: Arial, sans-serif; margin-top: 25px;">
            <p style="margin: 0; font-weight: bold; font-size: 14px; color: #0f172a;">{data['name']}</p>
            <p style="margin: 2px 0 5px 0; font-size: 12px; color: #475569;">{data['title']}</p>
            <p style="margin: 0; font-size: 12px; color: #2563eb;"><strong>{data['company']}</strong></p>
            <p style="margin: 4px 0 12px 0; font-size: 12px; color: #475569;">
                <a href="mailto:{data['email']}" style="color: #2563eb; text-decoration: none;">{data['email']}</a> | {data['phone']}
            </p>
            <img src="{data['logoUrl']}" alt="Company Logo" style="height: 45px; border-radius: 4px;" />
        </div>
        {DISCLAIMER_HTML}
        """

# --- HELPER FUNCTIONS ---
def render_template(template_str, row):
    def replace_var(match):
        key = match.group(1).lower().strip()
        val = row.get(key, "")
        return str(val) if pd.notna(val) and val != "" else f"[{match.group(1)}]"
    return re.sub(r'\{([^}]+)\}', replace_var, template_str)

def create_message(subject, html_body, to_addr, from_name, from_email):
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg

# --- SIDEBAR & HEADER ---
st.sidebar.image("https://mail.streamax.com/coremail/s?func=lp:getImg&org_id=&img_id=logo_001", width=150)
st.sidebar.markdown("<h1 class='aurora-text'>Drip Mailer</h1>", unsafe_allow_html=True)
st.sidebar.caption("By Trucking BU")

# Initialize Session State
if 'env_email' not in st.session_state:
    st.session_state['env_email'] = ""
if 'env_pass' not in st.session_state:
    st.session_state['env_pass'] = ""

tab0, tab1, tab2, tab3 = st.tabs(["0. Setup", "1. Compose", "2. Signatures", "3. Data & Sending"])

# --- TAB 0: SETUP ---
with tab0:
    st.markdown("<h2>Environment <span class='aurora-text'>Setup</span></h2>", unsafe_allow_html=True)
    st.write("To securely send emails from the cloud, enter your Streamax credentials here. They are temporarily held in memory for this session only and are never saved to a database.")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            input_email = st.text_input("Streamax Email", value=st.session_state['env_email'], placeholder="name@streamax.com")
        with col2:
            input_pass = st.text_input("Email Password", value=st.session_state['env_pass'], type="password", placeholder="••••••••")
        
        if st.button("Save Credentials to Session"):
            if input_email.endswith("@streamax.com") and input_pass:
                st.session_state['env_email'] = input_email
                st.session_state['env_pass'] = input_pass
                st.success("Credentials saved to active session! You can now proceed to Compose.")
            else:
                st.error("Please provide a valid @streamax.com email and password.")

# --- TAB 1: COMPOSE ---
with tab1:
    st.markdown("<h2>Compose <span class='aurora-text'>Email</span></h2>", unsafe_allow_html=True)
    st.write("Use variables like `{first_name}`, `{company}`, `{role}`.")
    
    col1, col2 = st.columns(2)
    with col1:
        subject_template = st.text_input("Subject Line", "Streamlining Operations at {company}")
        body_template = st.text_area("Email Body", DEFAULT_BODY, height=350)
    with col2:
        st.caption("Live Preview (Sample Data)")
        sample_row = {"first_name": "John", "company": "Acme Corp", "role": "Manager"}
        st.markdown(f"**Subject:** {render_template(subject_template, sample_row)}")
        st.info(render_template(body_template, sample_row).replace('\n', '\n\n'))

# --- TAB 2: SIGNATURES ---
with tab2:
    st.markdown("<h2>Email <span class='aurora-text'>Signature</span></h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        sig_name = st.text_input("Full Name", "Jane Doe")
        sig_title = st.text_input("Job Title", "Sales Director")
        sig_phone = st.text_input("Phone", "(555) 123-4567")
        sig_website = st.text_input("Website", "https://www.streamax.com")
        sig_avatar = st.text_input("Avatar URL", "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=120&q=80")
        sig_logo = st.text_input("Logo URL", "https://mail.streamax.com/coremail/s?func=lp:getImg&org_id=&img_id=logo_001")
        st.caption(f"Email: {st.session_state['env_email'] or 'Will use Setup Email'}")
        
    sig_data = {
        "name": sig_name, "title": sig_title, "company": "Streamax Technology", 
        "phone": sig_phone, "email": st.session_state['env_email'] or "your.email@streamax.com", 
        "website": sig_website, "avatarUrl": sig_avatar, "logoUrl": sig_logo
    }

    with col2:
        sig_layout = st.radio("Select Layout", ["Minimalist Professional", "Creative with Avatar", "Corporate with Logo"])
        selected_sig_html = get_signature_html(sig_layout, sig_data)
        st.markdown("<div style='background: white; padding: 20px; border-radius: 10px; color: black;'>" + selected_sig_html + "</div>", unsafe_allow_html=True)

# --- TAB 3: DATA & SENDING ---
with tab3:
    st.markdown("<h2>Data & <span class='aurora-text'>Sending</span></h2>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload leadList.csv", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            # Standardize columns for mapping
            df.columns = [str(c).lower().strip() for c in df.columns]
            required = ['first_name', 'last_name', 'email', 'role', 'company']
            missing = [r for r in required if r not in df.columns]
            
            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
            else:
                st.dataframe(df.head(10), use_container_width=True)
                
                if st.button("INITIATE BATCH SEND", type="primary"):
                    if not st.session_state['env_email'] or not st.session_state['env_pass']:
                        st.error("Missing Credentials! Please go back to Tab 0 (Setup) and enter your Streamax login.")
                    else:
                        progress_bar = st.progress(0)
                        log_container = st.empty()
                        logs = []
                        
                        try:
                            # SMTP Connection
                            context = smtplib.ssl.create_default_context() if True else None
                            server = smtplib.SMTP_SSL("mail.streamax.com", 465, timeout=30)
                            server.login(st.session_state['env_email'], st.session_state['env_pass'])
                            
                            total = len(df)
                            for index, row in df.iterrows():
                                target_email = row.get('email')
                                if pd.isna(target_email):
                                    continue
                                
                                # Render Email
                                rendered_subj = render_template(subject_template, row)
                                rendered_body = render_template(body_template, row)
                                html_content = rendered_body.replace('\n', '<br>') + f"<br><br>{selected_sig_html}"
                                
                                msg = create_message(rendered_subj, html_content, target_email, sig_name, st.session_state['env_email'])
                                
                                # Send
                                try:
                                    server.send_message(msg)
                                    logs.append(f"✅ [{time.strftime('%X')}] Sent successfully to {target_email}")
                                except Exception as e:
                                    logs.append(f"❌ [{time.strftime('%X')}] Failed to send to {target_email}: {str(e)}")
                                
                                # Update UI
                                progress_bar.progress((index + 1) / total)
                                log_container.code('\n'.join(logs[-10:]), language='text')
                                time.sleep(0.5)
                                
                            server.quit()
                            st.success("Batch Processing Complete!")
                            
                        except Exception as e:
                            st.error(f"SMTP Connection Error: {str(e)}")
        except Exception as e:
            st.error(f"Error reading CSV: {str(e)}")
