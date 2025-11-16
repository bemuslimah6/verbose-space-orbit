import streamlit as st
import random
import time
import pandas as pd
import os
from datetime import datetime
import uuid

st.set_page_config(page_title="Studi: Ketergantungan AI & Kinerja Memori (Digit Span)", layout="centered")

DATA_FILE = "data_responses.csv"
DISPLAY_DURATION = 2.5

def generate_participant_id():
    return datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]

def save_response(row: dict):
    df = pd.DataFrame([row])
    if not os.path.exists(DATA_FILE):
        df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(DATA_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def sync_to_gsheet(row: dict):
    try:
        if 'gspread_service_account' not in st.secrets:
            return False
        import json
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials

        sa_json = json.loads(st.secrets['gspread_service_account'])
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_json, scope)
        gc = gspread.authorize(creds)
        sheet_name = st.secrets.get('gspread_sheet_name', None)
        if not sheet_name:
            return False
        sh = gc.open(sheet_name)
        worksheet = sh.sheet1
        header = worksheet.row_values(1)
        if not header:
            worksheet.append_row(list(row.keys()))
            header = worksheet.row_values(1)
        worksheet.append_row([str(row.get(k, '')) for k in header])
        return True
    except Exception as e:
        st.warning(f"GSheet sync failed: {e}")
        return False

if 'participant_id' not in st.session_state:
    st.session_state['participant_id'] = generate_participant_id()

if 'stage' not in st.session_state:
    st.session_state['stage'] = 'consent'

if 'digit_index' not in st.session_state:
    st.session_state['digit_index'] = 0

if 'digit_lengths' not in st.session_state:
    st.session_state['digit_lengths'] = [3,3,4,4,5,5,6,6,7,7,8,8]

if 'forward_sequences' not in st.session_state:
    st.session_state['forward_sequences'] = []

if 'backward_sequences' not in st.session_state:
    st.session_state['backward_sequences'] = []

if 'forward_answers' not in st.session_state:
    st.session_state['forward_answers'] = [None]*12

if 'backward_answers' not in st.session_state:
    st.session_state['backward_answers'] = [None]*12

if 'forward_scores' not in st.session_state:
    st.session_state['forward_scores'] = [0]*12

if 'backward_scores' not in st.session_state:
    st.session_state['backward_scores'] = [0]*12

if 'demographics' not in st.session_state:
    st.session_state['demographics'] = {'initial': None, 'age': None, 'gender': None, 'education': None}

if 'q_answers' not in st.session_state:
    st.session_state['q_answers'] = {}

if 'timestamps' not in st.session_state:
    st.session_state['timestamps'] = {}

if 'saved' not in st.session_state:
    st.session_state['saved'] = False

st.title("Penelitian: Ketergantungan AI & Kinerja Memori (Digit Span)")
st.write("Aplikasi ini menggabungkan kuesioner ketergantungan AI dan tes Digit Span (Forward & Backward) untuk menguji kinerja memori.")

if st.session_state['stage'] == 'consent':
    st.header('Informed Consent (singkat)')
    st.write("""
    Kamu akan mengisi kuesioner tingkat ketergantungan AI dan melakukan tes Digit Span untuk menguji kinerja memori.
    Data bersifat anonim dan hanya digunakan untuk keperluan penelitian.
    """)
    
    agree = st.checkbox("Saya setuju berpartisipasi")

    if agree:
        st.session_state['demographics']['initial'] = st.text_input('Inisial')
        st.session_state['demographics']['age'] = st.number_input('Usia', 18, 80, 20)
        st.session_state['demographics']['gender'] = st.selectbox('Jenis kelamin', 
                ['Perempuan','Laki-laki','Lainnya','Prefer not to say'])
        st.session_state['demographics']['education'] = st.selectbox('Pendidikan', 
                ['SMA','Diploma','S1','S2','S3','Lainnya'])

        if st.button("Mulai Kuesioner"):
            st.session_state['timestamps']['consent_time'] = datetime.utcnow().isoformat()
            st.session_state['stage'] = 'questionnaire'

q_items = [
    "1. Saya sering meminta bantuan AI ketika harus mengingat informasi penting.",
    "2. Saya menggunakan AI untuk menyelesaikan tugas yang membutuhkan konsentrasi.",
    "3. Saat saya tidak ingat sesuatu, saya langsung mencari jawaban pada AI.",
    "4. Saya mengandalkan AI untuk mencari ide atau solusi sehari-hari.",
    "5. Saya menggunakan AI untuk mengatur pengingat atau jadwal saya.",
    "6. Saya percaya jawaban AI lebih cepat dan andal daripada mengandalkan ingatan sendiri.",
    "7. Saya lebih memilih menanyakan AI daripada mencoba mengingat sendiri.",
    "8. Saya cenderung menerima saran AI tanpa mengecek ulang.",
    "9. Saya merasa cemas jika tidak dapat mengakses AI.",
    "10. Saya sengaja tidak melatih ingatan karena ada AI."
]

if st.session_state['stage'] == 'questionnaire':
    st.header("Kuesioner Ketergantungan AI")
    st.write("1 = sangat tidak setuju ... 5 = sangat setuju")

    for i, item in enumerate(q_items, start=1):
        st.session_state['q_answers'][f'q{i}'] = st.radio(item, [1,2,3,4,5], key=f'q{i}')

    if st.button("Lanjut ke Digit Span"):
        st.session_state['q_total'] = sum(int(st.session_state['q_answers'][f'q{i}']) for i in range(1, 11))
        st.session_state['timestamps']['questionnaire_completed'] = datetime.utcnow().isoformat()
        st.session_state['stage'] = 'forward_intro'

if st.session_state['stage'] == 'forward_intro':
    st.header('Digit Span — Forward')
    st.write('Akan ada 12 sesi. Angka muncul sebentar lalu hilang, ketik ulang angka pada kolom jawaban mulai dari depan')

    if st.button("Mulai Forward"):
        st.session_state['forward_sequences'] = [
            [random.randint(1,9) for _ in range(n)]
            for n in st.session_state['digit_lengths']
        ]
        st.session_state['forward_answers'] = [None]*12
        st.session_state['forward_scores'] = [0]*12

        st.session_state['digit_index'] = 0
        st.session_state['timestamps']['forward_start'] = datetime.utcnow().isoformat()
        st.session_state['stage'] = 'forward_show'

if st.session_state['stage'] == 'forward_show':
    idx = st.session_state['digit_index']
    seq = st.session_state['forward_sequences'][idx]

    st.header(f"Forward Trial {idx+1}/12")
    placeholder = st.empty()
    placeholder.markdown(f"## **{' '.join(map(str, seq))}**")

    time.sleep(DISPLAY_DURATION)
    placeholder.empty()

    st.session_state['stage'] = 'forward_input'
    st.rerun()

if st.session_state['stage'] == 'forward_input':
    idx = st.session_state['digit_index']

    st.header(f"Forward Trial {idx+1}/12")
    ans = st.text_input("Masukkan ulang angka (tanpa spasi):", key=f"fw{idx}")

    if st.button("Submit Jawaban"):
        user_answer = ans.strip()
        correct_answer = ''.join(map(str, st.session_state['forward_sequences'][idx]))

        st.session_state['forward_answers'][idx] = user_answer
        st.session_state['forward_scores'][idx] = 1 if user_answer == correct_answer else 0

        st.session_state['digit_index'] += 1

        if st.session_state['digit_index'] >= 12:
            st.session_state['timestamps']['forward_end'] = datetime.utcnow().isoformat()
            st.session_state['digit_index'] = 0
            st.session_state['stage'] = 'backward_intro'
        else:
            st.session_state['stage'] = 'forward_show'

if st.session_state['stage'] == 'backward_intro':
    st.header("Digit Span — Backward")
    st.write("Pada sesi ini, Kamu harus mengetik angka secara terbalik dari belakang ke depan.")

    if st.button("Mulai Backward"):
        st.session_state['backward_sequences'] = [
            [random.randint(1,9) for _ in range(n)]
            for n in st.session_state['digit_lengths']
        ]
        st.session_state['backward_answers'] = [None]*12
        st.session_state['backward_scores'] = [0]*12

        st.session_state['digit_index'] = 0
        st.session_state['timestamps']['backward_start'] = datetime.utcnow().isoformat()
        st.session_state['stage'] = 'backward_show'

if st.session_state['stage'] == 'backward_show':
    idx = st.session_state['digit_index']
    seq = st.session_state['backward_sequences'][idx]

    st.header(f"Backward Trial {idx+1}/12")

    placeholder = st.empty()
    placeholder.markdown(f"## **{' '.join(map(str, seq))}**")

    time.sleep(DISPLAY_DURATION)
    placeholder.empty()

    st.session_state['stage'] = 'backward_input'
    st.rerun()

if st.session_state['stage'] == 'backward_input':
    idx = st.session_state['digit_index']
    seq = st.session_state['backward_sequences'][idx]

    st.header(f"Backward Trial {idx+1}/12")
    ans = st.text_input("Masukkan angka terbalik:", key=f"bw{idx}")

    if st.button("Submit Jawaban"):
        user_answer = ans.strip()
        correct_answer = ''.join(map(str, seq[::-1]))

        st.session_state['backward_answers'][idx] = user_answer
        st.session_state['backward_scores'][idx] = 1 if user_answer == correct_answer else 0

        st.session_state['digit_index'] += 1

        if st.session_state['digit_index'] >= 12:
            st.session_state['timestamps']['backward_end'] = datetime.utcnow().isoformat()
            st.session_state['stage'] = 'result'
        else:
            st.session_state['stage'] = 'backward_show'

if st.session_state['stage'] == 'result':
    st.header("Hasil Tes")

    forward_correct = sum(st.session_state['forward_scores'])
    backward_correct = sum(st.session_state['backward_scores'])

    st.write(f"Forward benar: {forward_correct} / 12")
    st.write(f"Backward benar: {backward_correct} / 12")
    st.write("---")
    st.write(f"Skor total: {forward_correct + backward_correct} / 24")
    st.write("---")
    st.write(f"Skor ketergantungan AI: {st.session_state.get('q_total')}")

    if not st.session_state.get('saved', False):
        row = {
            'inisial': st.session_state['demographics'].get('initial', ''),
            'age': st.session_state['demographics'].get('age', ''),
            'gender': st.session_state['demographics'].get('gender', ''),
            'education': st.session_state['demographics'].get('education', ''),


            **{f"q{i}": st.session_state['q_answers'].get(f'q{i}', '') for i in range(1, 11)},
            'q_total': st.session_state.get('q_total', ''),

            **{f"fw{i+1}": st.session_state['forward_scores'][i] for i in range(12)},
            **{f"bw{i+1}": st.session_state['backward_scores'][i] for i in range(12)},

            'forward_correct': forward_correct,
            'backward_correct': backward_correct,
        }

        try:
            save_response(row)
            sync_to_gsheet(row)
            st.success("Data berhasil disimpan. Terima kasih telah berpartisipasi!")
        except Exception as e:
            st.error(f"Gagal menyimpan data: {e}")

        st.session_state['saved'] = True


    if st.session_state.get('saved', False):
        st.session_state['stage'] = 'finished'
        st.rerun()



if st.session_state['stage'] == 'finished':

    st.balloons()
    st.header("Selesai!")
    st.write("Terima kasih telah berpartisipasi dalam penelitian kami")


st.sidebar.header("Admin")
st.sidebar.write("Participant:", st.session_state['participant_id'])

if st.sidebar.button("Reset & New Participant"):

    st.session_state.clear()
