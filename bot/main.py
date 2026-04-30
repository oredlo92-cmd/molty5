import os
import requests
import time
import json
from google import genai # Memakai pustaka resmi Google GenAI

class MoltyGeminiAgent:
    def __init__(self):
        # 1. Konfigurasi API Server Game
        self.base_url = "https://moltyroyale.com"
        self.api_key = os.getenv("API_KEY", "21ae88b7-7323-4133-8f36-6bb831aa9590")
        self.headers = {
            "X-API-Key": self.api_key,
            "X-Version": "1.6.0"
        }
        
        # 2. Inisialisasi Otak AI (Google Gemini)
        # Pastikan kamu memasukkan GEMINI_API_KEY di variabel Railway
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # State Internal
        self.game_id = None
        self.agent_id = None

    def start_game(self):
        try:
            print("[SISTEM] Mencari room yang tersedia...")
            resp = requests.get(f"{self.base_url}/games?status=waiting", headers=self.headers, timeout=10)
            
            if resp.status_code != 200:
                print(f"[ERROR] Gagal kontak server. Code: {resp.status_code}")
                return False
                
            games = resp.json().get("data", [])
            if not games:
                print("[SISTEM] Tidak ada game yang berstatus 'waiting'.")
                return False
            
            self.game_id = games[0]["id"]
            
            print(f"[SISTEM] Mendaftarkan Agent ke Room ID: {self.game_id}")
            res = requests.post(
                f"{self.base_url}/games/{self.game_id}/agents/register",
                headers=self.headers,
                json={"name": "Gemini_Agent_Ultimatum"},
                timeout=10
            )
            
            data = res.json().get("data")
            if data:
                self.agent_id = data["id"]
                print(f"[SISTEM] BERHASIL DAFTAR! Agent ID: {self.agent_id}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"[ERROR] Masalah pada start_game: {e}")
            return False

    def run_logic(self):
        print("[SISTEM] Agent AI Gemini Aktif. Memulai game loop...")
        while True:
            try:
                resp = requests.get(f"{self.base_url}/games/{self.game_id}/agents/{self.agent_id}/state", headers=self.headers, timeout=10)
                game_state = resp.json().get("data")
                
                if not game_state or not game_state["self"]["isAlive"]:
                    print("[SISTEM] Agent Anda gugur atau permainan telah usai.")
                    break
                
                action_pilihan_ai = self.ask_gemini_for_decision(game_state)
                self.post_action(action_pilihan_ai)
                
                time.sleep(60)
                
            except Exception as e:
                print(f"[SISTEM] Error: {e}. Mengulang dalam 10 detik.")
                time.sleep(10)

    def ask_gemini_for_decision(self, game_state):
        print("[AI] Gemini sedang menganalisa situasi...")
        
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
            # Menggunakan model Gemini 2.5 Flash yang sangat cepat dan gratis
            response = self.ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            # Membersihkan kemungkinan spasi/karakter aneh di luar JSON yang dikirimkan AI
            clean_text = response.text.strip().replace("```json", "").replace("```", "")
            ai_decision = json.loads(clean_text)
            
            print(f"[AI Decision] Taktik dirumuskan: {ai_decision.get('type')}")
            return ai_decision
            
        except Exception as e:
            print(f"[AI ERROR] Gagal kontak Gemini: {e}. Menggunakan fallback 'explore'.")
            return {"type": "explore"}

    def post_action(self, action):
        try:
            payload = {
                "action": action,
                "thought": {"reasoning": f"Gemini move: {action.get('type')}"}
            }
            requests.post(
                f"{self.base_url}/games/{self.game_id}/agents/{self.agent_id}/action", 
                headers=self.headers, 
                json=payload, 
                timeout=10
            )
        except Exception as e:
            print(f"[ERROR] Gagal kirim aksi: {e}")

if __name__ == "__main__":
    bot = MoltyGeminiAgent()
    if bot.start_game():
        bot.run_logic()
