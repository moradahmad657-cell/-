import streamlit as st
import requests
import time
import json

# ----------------- الإعدادات الأولية والمفاتيح -----------------
API_KEY = "AQ.Ab8RN6KOxr1GiqaIQnMArxvqXndhrNV2_MJM2lrzIv0WNeKNGg"

MODELS_TO_TRY = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite",
    "gemini-4-argon",
    "gemini-omni-1.1-flash"
]

# ----------------- واجهة المستخدم -----------------
st.set_page_config(page_title="مساعد صيانة شبكات الكهرباء - IDECO", layout="wide", page_icon="⚡")

col1, col2 = st.columns([1, 4])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3233/3233483.png", width=100) # أيقونة رمزية للطاقة
with col2:
    st.title("⚡ مساعد صيانة وإصلاح أعطال شبكات الجهد المنخفض (IDECO)")
    
st.info("✅ النظام متصل الآن عبر مسار النماذج المتقدمة مع ميزة التبديل التلقائي لتجاوز القيود (Failover).")

# ----------------- قاعدة البيانات (مدمجة) -----------------
KNOWLEDGE_BASE_JSON = """
{
  "faults": [
    {"fault_id": "LV_PQ_001", "fault_name": "انخفاض الفولتية", "description": "تراجع الجهد عن 207 فولت.", "symptoms": ["تفاوت الإضاءة", "فصل الأجهزة (Safe Mode)"], "repair_sequence": ["الفحص الأولي", "تشخيص نوع الانخفاض", "معالجة انخفاض جميع الفازات", "معالجة انخفاض فاز واحد (إعادة التوزيع)"]},
    {"fault_id": "LV_PQ_002", "fault_name": "ارتفاع الفولتية", "description": "ارتفاع الجهد فوق 253 فولت.", "symptoms": ["تلف وعمل حمايات الأجهزة"], "repair_sequence": ["التشخيص الأولي", "معالجة ارتفاع جميع الفازات (تنزيل Tap Changer)", "تأكيد سلامة النيوترال", "إعادة توزيع الأحمال"]},
    {"fault_id": "LV_NET_001", "fault_name": "النيوترال المكهرب (NEV)", "description": "فولتية بين N و E.", "measurements_required": {"network": ["قياس Zero-Sequence Current بالسناب"]}, "repair_sequence": ["تحديد الفاز المسبب (بالمحطة)", "استخدام Clamp Meter على الكيبل كاملاً", "تتبع المفصل المسبب للعطل"]},
    {"fault_id": "LV_NET_002", "fault_name": "انقطاع خط النيوترال", "description": "انزياح نقطة التعادل وتفاوت الجهود بشدة.", "repair_sequence": ["فصل فازين كإجراء وقائي للمشتركين", "تتبع تيار النيوترال تنازلياً، النقطة صفر أمبير تقع بعد القطع"]},
    {"fault_id": "LV_NET_003", "fault_name": "انقطاع خط فاز", "description": "فولتية صفر على فاز واحد.", "repair_sequence": ["تتبع تيار الفاز بالـ Clamp Meter حتى الوصول لقراءة صفر أمبير بعد المفصل"]},
    {"fault_id": "LV_NET_004", "fault_name": "كيبل أرضي ضارب", "description": "انهيار عازلية، شورت سيركت واحتراق الفيوز.", "repair_sequence": ["فحص مقاومة الفيوز", "الفحص التقاطعي لتماس الأطوار", "فصل الكابل الأرضي وفحصه بجهاز Megger"]},
    {"fault_id": "LV_NET_005", "fault_name": "فيوز محروق", "description": "انصهار الفيوز لزيادة حمل أو شورت.", "repair_sequence": ["فحص الفولتية والمقاومة", "تبديل الفيوز بحذر", "إذا فصل فورا، تتبع تماس. إذا لم يفصل، قِس الأحمال."]}
  ]
}
"""

system_instruction = f"""
# Role & Identity
أنت مساعد ذكي ونظام خبير (Expert System) مصمم خصيصاً لمهندسي وفنيي شركة كهرباء إربد (IDECO). دورك هو المساعدة في تشخيص وإصلاح أعطال شبكة الجهد المنخفض بناءً على الدليل الميداني التشغيلي المعتمد المرفق في قاعدة بياناتك (JSON).

# Core Objectives
1. تحليل البلاغات وشكاوى المشتركين وربطها بالأعطال الموجودة في قاعدة البيانات.
2. عدم إعطاء الحل النهائي مباشرة، بل توجيه الفني خطوة بخطوة من خلال طلب "القياسات المطلوبة".
3. تأكيد العطل بناءً على قراءات الفني، ثم استعراض معدات السلامة (PPE).
4. تزويد الفني بخطوات الإصلاح (Repair Sequence) خطوة بخطوة والتأكد من إنجاز كل خطوة قبل الانتقال للتالية.

# Constraints
- يُمنع منعاً باتاً اقتراح خطوات إصلاح أو أعطال غير موجودة في قاعدة بيانات JSON المرفقة.
- التزم دائماً بأعلى معايير السلامة المهنية، وذكّر الفني بارتداء معدات الوقاية المناسبة للعطل.
- اسأل سؤالاً واحداً في كل مرة، وانتظر إجابة الفني.
- استخدم المصطلحات الهندسية المعتمدة (Zero-Sequence Current, Clamp Meter, Megger, Tap Changer).

# Database (JSON Overview)
{KNOWLEDGE_BASE_JSON}
"""

# ----------------- إدارة الجلسة (Chat History) -----------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "مرحباً بك في نظام IDECO الخبير الميداني. أنا هنا لمساعدتك في تشخيص العطل. يرجى تزويدي بتفاصيل البلاغ أو شكوى المشترك لنبدأ التشخيص خطوة بخطوة."}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ----------------- معالجة الإدخال والاتصال بالـ API -----------------
if prompt := st.chat_input("اكتب تفاصيل البلاغ هنا (مثلاً: مشترك يشتكي من ضعف إضاءة، أو انقطاع على فاز واحد)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # تجميع السياق
        full_prompt = f"التعليمات للنظام الخبير:\n{system_instruction}\n\nسياق المحادثة:\n"
        for msg in st.session_state.messages:
            role_ar = 'المستخدم (الفني)' if msg['role'] == 'user' else 'النظام الخبير (IDECO)'
            full_prompt += f"{role_ar}: {msg['content']}\n"

        payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
        session = requests.Session()
        session.trust_env = False

        success = False
        
        # حلقة (Loop) لتجربة النماذج وتجاوز القيود (429 و 503)
        for model_name in MODELS_TO_TRY:
            if success:
                break
                
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
            message_placeholder.markdown(f"⏳ جاري التحليل والربط مع قاعدة البيانات عبر موديل (`{model_name}`)...")
            
            for attempt in range(1, 3):
                try:
                    response = session.post(api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=35)
                    
                    if response.status_code == 200:
                        data = response.json()
                        reply = data['candidates'][0]['content']['parts'][0]['text']
                        message_placeholder.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        success = True
                        break
                    elif response.status_code == 429:
                        message_placeholder.warning(f"⚠️ انتهت الحصة (Quota) لموديل {model_name}، جاري التبديل التلقائي للموديل التالي...")
                        time.sleep(1.5)
                        break  
                    elif response.status_code == 503:
                        time.sleep(2)  
                    else:
                        break  
                except requests.exceptions.RequestException:
                    time.sleep(2)

        if not success:
            message_placeholder.error("❌ عذراً، جميع النماذج تواجه ضغطاً حالياً أو استنفدت الحصة اليومية. يرجى المحاولة بعد قليل.")
