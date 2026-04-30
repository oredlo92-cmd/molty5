import os
import json
from google import genai
from bot.utils.logger import get_logger

log = get_logger(__name__)

class AggressiveAgent:
    # Tambahkan 'heartbeat=None' agar tidak error saat dipanggil oleh main.py
    def __init__(self, heartbeat=None):
        self.heartbeat = heartbeat
        # Inisialisasi AI Gemini
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
    def run_logic(self, game_state):
        """Fungsi ini yang akan dipanggil otomatis oleh Heartbeat setiap turn."""
        if not game_state or not game_state.get("self", {}).get("isAlive"):
            return None

        log.info("[AI] Gemini sedang menganalisa situasi...")
        
        prompt = f"""
        Kamu adalah AI Agent dalam game battle-royale top-down bernama Molty Royale.
        Tugas utamamu adalah bertahan hidup sampai Day 16 00:00 dan mengumpulkan token sMoltz sebanyak mungkin.
        
        Kondisi game saat ini dalam bentuk JSON:
        {json.dumps(game_state)}
        
        Aturan Dasar:
        1. Jika berada di zona maut ('isDeathZone': true), WAJIB gunakan aksi 'move' ke region koneksi yang aman.
        2. Jika HP di bawah 30, utamakan menggunakan item penyembuh ('use_item') atau mencari 'Medical Facility'.
        3. Menyerang (attack) membutuhkan minimal 2 EP. Jangan membuang giliran menyerang jika EP kurang.
        4. Jika tidak ada musuh atau target, lakukan 'explore' untuk mencari item seperti Katana atau Sniper.
        5. Batasi diri maksimal membawa 8 item di inventaris agar sisa 2 slot kosong bisa menerima bantuan Sponsor.
        
        Kamu HANYA BOLEH merespon output dalam format JSON murni tanpa ada penjelasan teks pembuka atau penutup sama sekali.
        Contoh Respons JSON yang valid:
        {{"type": "attack", "targetId": "musuh_id", "targetType": "agent"}} atau {{"type": "explore"}} atau {{"type": "rest"}}
        """
        
        try:
            # Memanggil model Gemini 2.5 Flash yang gratis
            response = self.ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            # Membersihkan teks dari blok markdown JSON jika ada
            clean_text = response.text.strip().replace("```json", "").replace("```", "")
            ai_decision = json.loads(clean_text)
            
            log.info(f"[AI Decision] Taktik dirumuskan: {ai_decision.get('type')}")
            return ai_decision
            
        except Exception as e:
            log.error(f"[AI ERROR] Gagal kontak Gemini: {e}")
            # Fallback jika AI gagal berpikir, kembalikan aksi standar
            return {"type": "explore"}
