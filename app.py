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

# --- CUSTOM CSS (Dark Theme + Streamax Green) ---
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #050810;
        background-image: radial-gradient(circle at 50% -20%, #111827, #050810);
        color: #E2E8F0;
    }
    h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; }
    p, span, label { color: #E2E8F0; }
    
    /* Buttons */
    .stButton>button {
        background-color: #00A859;
        color: #FFFFFF;
        font-weight: 600;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #008C4A;
        color: #FFFFFF;
        box-shadow: 0 4px 10px rgba(0, 168, 89, 0.4);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(255, 255, 255, 0.05);
        color: #FFFFFF;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #00A859;
        box-shadow: 0 0 0 1px #00A859;
    }
    
    /* Brand Text Highlight */
    .brand-text {
        color: #00A859;
        font-weight: bold;
    }
    
    /* Hide default header */
    header { visibility: hidden; }
    
    /* Tab Styling Override for Dark Theme */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        color: #00A859 !important;
        border-bottom-color: #00A859 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div style="display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
    <img src="https://mail.streamax.com/coremail/s?func=lp:getImg&org_id=&img_id=logo_001" style="height: 50px; filter: brightness(0) invert(1);" />
    <div>
        <h1 style="margin: 0; padding: 0; font-size: 32px; line-height: 1.1; color: #FFFFFF;">Drip Mailer</h1>
        <p style="margin: 0; padding: 0; color: #00A859; font-weight: 600; font-size: 15px;">By Trucking BU</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if 'env_email' not in st.session_state: st.session_state['env_email'] = ""
if 'env_pass' not in st.session_state: st.session_state['env_pass'] = ""
if 'sig_name' not in st.session_state: st.session_state['sig_name'] = "Jane Doe"
if 'sig_title' not in st.session_state: st.session_state['sig_title'] = "Sales Director"
if 'sig_phone' not in st.session_state: st.session_state['sig_phone'] = "(555) 123-4567"
if 'sig_website' not in st.session_state: st.session_state['sig_website'] = "https://www.streamax.com"
if 'sig_avatar' not in st.session_state: st.session_state['sig_avatar'] = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=120&q=80"
if 'sig_logo' not in st.session_state: st.session_state['sig_logo'] = "https://mail.streamax.com/coremail/s?func=lp:getImg&org_id=&img_id=logo_001"
if 'sig_layout' not in st.session_state: st.session_state['sig_layout'] = "Creative with Avatar"

# --- DEFAULTS & TEMPLATES ---
DEFAULT_BODY = """Hi {first_name},

I hope this email finds you well. I noticed that {company} is doing some incredible work lately.

As someone working as a {role}, I thought you might be interested in how our new tools can help streamline your daily operations. We've helped similar teams increase their efficiency by over 20%.

Would you be open to a brief 10-minute chat next week?

Best regards,"""

# Tightly packed HTML to prevent Streamlit from rendering them as Markdown code blocks
DISCLAIMER_HTML = (
    '<div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-family: Arial, sans-serif; font-size: 10px; color: #64748b; line-height: 1.4; text-align: justify;">'
    '<strong>Email Disclaimer:</strong> This e-mail is intended only for the person or entity to which it is addressed and may contain confidential and/or privileged material. Any review, retransmission, dissemination or other use of, or taking of any action in reliance upon, the information in this e-mail by persons or entities other than the intended recipient is prohibited and may be unlawful. If you received this e-mail in error, please contact the sender and delete it from any computer.'
    '</div>'
)

def get_signature_html(sig_id, data):
    if sig_id == "Minimalist Professional":
        html = (
            '<div style="font-family: Arial, sans-serif; color: #333; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">'
            f'<p style="margin: 0; font-weight: bold; font-size: 14px; color: #000000;">{data["name"]}</p>'
            f'<p style="margin: 0; font-size: 12px; color: #666;">{data["title"]} | {data["company"]}</p>'
            f'<p style="margin: 0; font-size: 12px; color: #0066cc;">{data["email"]} | {data["phone"]}</p>'
            '</div>'
        )
        return html + DISCLAIMER_HTML
    elif sig_id == "Creative with Avatar":
        html = (
            '<div style="font-family: \'Helvetica Neue\', Helvetica, Arial, sans-serif; margin-top: 20px; display: flex; align-items: center; gap: 15px;">'
            f'<img src="{data["avatarUrl"]}" alt="Avatar" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #e2e8f0;" />'
            '<div>'
            f'<p style="margin: 0; font-weight: 600; font-size: 15px; color: #1e293b;">{data["name"]}</p>'
            f'<p style="margin: 2px 0; font-size: 13px; color: #64748b;">{data["title"]}</p>'
            f'<p style="margin: 2px 0; font-size: 13px; color: #3b82f6;">{data["email"]} <span style="color: #94a3b8;">|</span> <span style="color: #64748b;">{data["phone"]}</span></p>'
            f'<a href="{data["website"]}" style="margin: 0; font-size: 13px; color: #3b82f6; text-decoration: none;">{data["website"].replace("https://", "")}</a>'
            '</div></div>'
        )
        return html + DISCLAIMER_HTML
    else: # Corporate with Logo
        html = (
            '<div style="font-family: Arial, sans-serif; margin-top: 25px;">'
            f'<p style="margin: 0; font-weight: bold; font-size: 14px; color: #0f172a;">{data["name"]}</p>'
            f'<p style="margin: 2px 0 5px 0; font-size: 12px; color: #475569;">{data["title"]}</p>'
            f'<p style="margin: 0; font-size: 12px; color: #00A859;"><strong>{data["company"]}</strong></p>'
            f'<p style="margin: 4px 0 12px 0; font-size: 12px; color: #475569;"><a href="mailto:{data["email"]}" style="color: #00A859; text-decoration: none;">{data["email"]}</a> | {data["phone"]}</p>'
            f'<img src="{data["logoUrl"]}" alt="Company Logo" style="height: 45px; border-radius: 4px;" />'
            '</div>'
        )
        return html + DISCLAIMER_HTML

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

# Generate current signature html to share across tabs
sig_data = {
    "name": st.session_state['sig_name'],
    "title": st.session_state['sig_title'],
    "company": "Streamax Technology",
    "phone": st.session_state['sig_phone'],
    "email": st.session_state['env_email'] or "your.email@streamax.com",
    "website": st.session_state['sig_website'],
    "avatarUrl": st.session_state['sig_avatar'],
    "logoUrl": st.session_state['sig_logo']
}
selected_sig_html = get_signature_html(st.session_state['sig_layout'], sig_data)

# --- TAB SETUP ---
tab0, tab1, tab2, tab3 = st.tabs(["0. Setup", "1. Compose", "2. Signatures", "3. Data & Sending"])

# --- TAB 0: SETUP ---
with tab0:
    st.markdown("<h2>Environment <span class='brand-text'>Setup</span></h2>", unsafe_allow_html=True)
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
    st.markdown("<h2>Compose <span class='brand-text'>Email</span></h2>", unsafe_allow_html=True)
    st.write("Use variables like `{first_name}`, `{company}`, `{role}`.")
    
    col1, col2 = st.columns(2)
    with col1:
        subject_template = st.text_input("Subject Line", "Streamlining Operations at {company}")
        body_template = st.text_area("Email Body", DEFAULT_BODY, height=350)
    with col2:
        st.caption("Live HTML Preview (Sample Data)")
        sample_row = {"first_name": "John", "company": "Acme Corp", "role": "Manager"}
        
        rendered_subject = render_template(subject_template, sample_row)
        rendered_body_html = render_template(body_template, sample_row).replace('\n', '<br>')
        
        # Enhanced fully styled email preview card (White background for realistic preview)
        preview_html = (
            '<div style="background-color: #ffffff; color: #1e293b; padding: 24px; border-radius: 8px; border: 1px solid #cbd5e1; font-family: Arial, sans-serif; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">'
            '<div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 20px;">'
            '<span style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Subject:</span>'
            f'<span style="color: #0f172a; font-size: 15px; font-weight: bold; margin-left: 8px;">{rendered_subject}</span>'
            '</div>'
            '<div style="font-size: 14px; line-height: 1.6; color: #334155;">'
            f'{rendered_body_html}'
            '<br><br>'
            f'{selected_sig_html}'
            '</div></div>'
        )
        st.markdown(preview_html, unsafe_allow_html=True)

# --- TAB 2: SIGNATURES ---
with tab2:
    st.markdown("<h2>Email <span class='brand-text'>Signature</span></h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.text_input("Full Name", key="sig_name")
        st.text_input("Job Title", key="sig_title")
        st.text_input("Phone", key="sig_phone")
        st.text_input("Website", key="sig_website")
        st.text_input("Avatar URL", key="sig_avatar")
        st.text_input("Logo URL", key="sig_logo")
        st.caption(f"Email: {st.session_state['env_email'] or 'Will use Setup Email'}")

    with col2:
        st.radio("Select Layout", ["Minimalist Professional", "Creative with Avatar", "Corporate with Logo"], key="sig_layout")
        st.markdown("<div style='background: white; padding: 20px; border-radius: 8px; border: 1px solid #cbd5e1; color: black; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);'>" + selected_sig_html + "</div>", unsafe_allow_html=True)

# --- TAB 3: DATA & SENDING ---
with tab3:
    st.markdown("<h2>Data & <span class='brand-text'>Sending</span></h2>", unsafe_allow_html=True)
    
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
                                
                                msg = create_message(rendered_subj, html_content, target_email, st.session_state['sig_name'], st.session_state['env_email'])
                                
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
