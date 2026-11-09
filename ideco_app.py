import streamlit as st
import requests
import time

# مفتاحك المتقدم
API_KEY = "AQ.Ab8RN6Klzv5tw9x_O3SDS6KUdZ7qf_IZzA10EevhR8WfaKQ4IQ"

# قائمة الموديلات المتاحة في حسابك بترتيب الأولوية لتجاوز أي حصة منتهية (429)
MODELS_TO_TRY = [
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash"
]

st.set_page_config(page_title="مساعد صيانة شبكات الكهرباء - IDECO", layout="wide")
st.title("⚡ مساعد صيانة وإصلاح اعطال شبكات الجهد المنخفض")
st.info("✅ النظام متصل الآن عبر مسار النماذج المتقدمة مع ميزة التبديل التلقائي لتجاوز القيود.")

system_instruction = """
# Role & Identity
أنت مساعد ذكي ونظام خبير (Expert System) مصمم خصيصاً لمهندسي وفنيي شركة كهرباء إربد (IDECO). دورك هو المساعدة في تشخيص وإصلاح أعطال شبكة الجهد المنخفض بناءً على الدليل الميداني التشغيلي المعتمد المرفق في قاعدة بياناتك (JSON).

# Core Objectives
1. تحليل البلاغات وشكاوى المشتركين وربطها بالأعطال الموجودة في قاعدة البيانات.
2. عدم إعطاء الحل النهائي مباشرة، بل توجيه الفني خطوة بخطوة من خلال طلب "القياسات المطلوبة".
3. تأكيد العطل بناءً على قراءات الفني، ثم استعراض معدات السلامة (PPE).
4. تزويد الفني بخطوات الإصلاح (Repair Sequence) خطوة بخطوة والتأكد من إنجاز كل خطوة.

# Constraints
- يُمنع منعاً باتاً اقتراح خطوات إصلاح أو أعطال غير موجودة في قاعدة بيانات JSON المرفقة.
- التزم دائماً بأعلى معايير السلامة المهنية.

# Database (JSON)
{
  "fault_id": "LV_NEV_001",
  "fault_name": "النيوترال المكهرب (Neutral to Earth Voltage - NEV)",
  "description": "تشكل فولتية غير طبيعية بين النيوترال والأرضي نتيجة تماس أحد الأطوار (الفازات) مع الأرض أو الأجسام المعدنية المؤرضة.",
  "symptoms": [
    "اهتزاز ووميض الإضاءة (Voltage Flicker) وخاصة وحدات إنارة LED.",
    "فصل تلقائي لقواطع التسرب الأرضي (RCD / ELCB) في لوحة التوزيع الداخلية.",
    "دخول شواحن المركبات الكهربائية (EV) والأجهزة الحساسة في وضع الحماية التلقائي.",
    "الإحساس بلسعة كهربائية عند ملامسة النيوترال أو الأجسام المعدنية المؤرضة المتصلة بالشبكة."
  ],
  "measurements_required": {
    "customer_panel": [
      "قياس الجهد بين خط النيوترال والأرضي (N-E) بعد فتح القاطع الرئيسي للمشترك."
    ],
    "substation_distribution_box": [
      "قياس الجهد بين باسبار النيوترال وباسبار الأرضي (N-E).",
      "قياس الجهد بين كل طور (L1, L2, L3) والأرضي (E)."
    ],
    "distribution_network": [
      "قياس المجموع الاتجاهي للتيارات (Zero-Sequence Current) باستخدام Clamp Meter حول الكابل المجمع بالكامل.",
      "فحص الجهد الاستقرائي على هياكل أعمدة الإنارة باستخدام كاشف الجهد الخارجي."
    ]
  },
  "safety_ppe": [
    "قفازات عازلة للجهد المنخفض (Insulated Gloves)",
    "خوذة السلامة المهنية مع واقي الوجه (Safety Helmet with Face Shield)",
    "حذاء السلامة الكهربائي العازل (Dielectric Safety Shoes)",
    "ملابس العمل المقاومة للهب (Flame-Resistant Clothing)",
    "أدوات القياس المعزولة والمصرح بها (Multimeter, Clamp Meter, Voltage Detector)"
  ],
  "repair_sequence": [
    {
      "step_number": 1,
      "title": "عزل أحمال المشترك وإجراء الفحص الأولي",
      "action": "افتح القاطع الرئيسي للمشترك لعزل كافة الأحمال الداخلية تماماً، ثم قِس الجهد الكهربائي بين طرف النيوترال وطرف الأرضي بواسطة الملتيميتر."
    },
    {
      "step_number": 2,
      "title": "تحديد الفاز المسبب للعطل في المحطة",
      "action": "قِس الجهد بين باسبار النيوترال وباسبار الأرضي لمطابقة القراءة السابقة، ثم قِس الجهد بين كل فاز منفرد مع الأرضي."
    }
  ]
}
"""

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("اكتب تفاصيل البلاغ هنا (مثلاً: عندي مشترك بيشتكي من ضعف إضاءة وفصل الشاحن)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_prompt = f"التعليمات:\n{system_instruction}\n\nسياق المحادثة:\n"
        for msg in st.session_state.messages:
            full_prompt += f"{'المستخدم' if msg['role'] == 'user' else 'المساعد'}: {msg['content']}\n"

        payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
        session = requests.Session()
        session.trust_env = False

        success = False
        
        # المرور على الموديلات المتاحة تلقائياً، إذا انتهت حصة الأول يذهب للثاني
        for model_name in MODELS_TO_TRY:
            if success:
                break
                
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
            message_placeholder.markdown(f"⏳ جاري الاتصال بموديل ({model_name})...")
            
            for attempt in range(1, 3):
                try:
                    response = session.post(api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        reply = data['candidates'][0]['content']['parts'][0]['text']
                        message_placeholder.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        success = True
                        break
                    elif response.status_code == 429:
                        message_placeholder.warning(f"انتهت الحصة اليومية لموديل {model_name}، جاري التبديل للموديل التالي...")
                        time.sleep(1)
                        break # نكسر حلقة المحاولات لهذا الموديل وننتقل للموديل التالي في القائمة الرئيسية
                    elif response.status_code == 503:
                        time.sleep(2) # انتظار قليل بسبب الضغط وإعادة المحاولة على نفس الموديل
                    else:
                        break # أخطاء أخرى غير متوقعة
                except Exception:
                    time.sleep(2)

        if not success:
            message_placeholder.error("جميع الموديلات تواجه ضغطاً أو استنفدت حصتها. يرجى المحاولة بعد قليل.")