import os
import json
from google import genai
from bot.utils.logger import get_logger

log = get_logger(__name__)

class AggressiveAgent:
    def __init__(self, heartbeat=None):
        self.heartbeat = heartbeat
        # Inisialisasi AI Gemini
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
    def run_logic(self, game_state):
        """Fungsi ini akan dipanggil otomatis oleh Heartbeat setiap turn."""
        if not game_state or not game_state.get("self", {}).get("isAlive"):
            return None

        log.info("[AI] Gemini sedang menganalisa situasi...")
        
        prompt = f"""
        Kamu adalah Agent AI dalam game battle-royale top-down bernama Molty Royale.
        Tugas utamamu adalah bertahan hidup sampai Day 16 00:00 dan mengumpulkan token sMoltz sebanyak mungkin.
        
        Kondisi game saat ini dalam bentuk JSON:
        {json.dumps(game_state)}
        
        =========================================
        ATURAN RESMI GAME TERBARU (SANGAT PENTING):
        =========================================
        - Statistik Dasar: HP 100, EP Max 10 (+1 auto regen), ATK 10, DEF 5, Vision 1.
        - Rumus Damage: (ATK + weapon_bonus) - (target_DEF x 0.5). Minimal damage 1. Semua serangan butuh 2 EP!
        - Senjata: Dagger(+10 Atk), Sword(+20 Atk), Katana(+35 Atk), Bow(+5 Atk, Jarak 1), Pistol(+10 Atk, Jarak 1), Sniper(+28 Atk, Jarak 2).
        
        - SISTEM COOLDOWN:
          * Aksi 'cooldown' (Hanya boleh 1 per turn / 60 detik): 'move', 'attack', 'use_item', 'interact', 'rest'.
          * Aksi Bebas (0 EP, Tanpa Cooldown): 'pickup', 'equip', 'talk', 'whisper', 'broadcast'. Lakukan aksi bebas kapan saja!
          * PERINGATAN: Aksi 'explore' saat ini DINONAKTIFKAN oleh game. Jangan gunakan aksi 'explore'!
          
        - ZONA MATI (DEATH ZONE):
          * Memberikan damage 1.34 HP/detik terus menerus. Cek 'view.currentRegion.isDeathZone' setiap turn.
          * DILARANG KERAS bergerak ke wilayah yang ada di daftar 'view.pendingDeathzones'.
          * Aksi 'interact' diblokir total saat berada di dalam Death Zone!
          
        - SISTEM GUARDIAN:
          * Ada 5 Guardian per room dan mereka MENYERANG PEMAIN langsung! Anggap sebagai musuh berbahaya.
          * Di Free Room: Membunuh Guardian menjatuhkan 120 sMoltz.
          
        - SISTEM TERRAIN & CUACA:
          * Plains (+1 Vision), Forest (-1 Vision, bagus untuk sembunyi), Hills (+2 Vision), Ruins (Tingkat temuan item lebih tinggi).
          * Water (Biaya gerak nambah +1 EP, total butuh 3 EP!).
          * Cuaca Rain (-1 Vision, -5% damage), Fog (-2 Vision, -10% damage), Storm (-2 Vision, Biaya gerak nambah +1 EP / total 3 EP, -15% damage).
          
        - ITEM & FASILITAS:
          * Broadcast Station, Supply Cache (Dapatkan item acak), Medical Facility (Pulihkan HP), Watchtower (+2 Vision).
          * Cave (Bisa masuk/keluar. Jika masuk: vision -2, req +2, dan tidak bisa bergerak/Move).

        - ITEM RECOVERY & UTILITY:
          * Binoculars (+1 Vision pasif), Map (Buka peta sekali), Megaphone (Pesan global).
          * Emergency Food (+20 HP), Bandage (+30 HP), Medkit (+50 HP), Energy Drink (+5 EP).
          * Kapasitas tas MAKSIMAL 10 item. Jika penuh, pickup akan gagal!
          
        - SISTEM PEMIKIRAN (THOUGHT):
          * Kamu harus melampirkan objek 'thought' berisi {{ "reasoning": "alasanmu", "plannedAction": "aksi_rencana" }} di setiap respon.
          * Batasan Karakter: Maksimal reasoning 500 karakter, plannedAction 200 karakter. Jangan melebihi batas ini!
          
        =========================================
        ATURAN DASAR TINDAKAN BOT (LOGIKA KAMU):
        =========================================
        1. DI AWAL PERMAINAN: Kamu WAJIB memprioritaskan mencari senjata dan item penyembuh terlebih dahulu agar tidak tangan kosong.
        2. MANAJEMEN SENJATA: Jika melihat senjata dengan 'ATK Bonus' lebih tinggi di tanah, gunakan aksi 'pickup' dan 'equip' (Aksi Bebas!). Buang yang lemah.
        3. ANTI-GAS: Jika berada di Death Zone atau wilayahmu masuk daftar 'pendingDeathzones', prioritaskan aksi 'move' ke koneksi region yang aman.
        4. HEALING MAKSIMAL: Jika HP-mu belum mencapai 100 dan kamu masih memiliki item penyembuh (Bandage/Medkit/Food) di dalam tas, gunakan aksi 'use_item' terus sampai HP-mu menyentuh angka 100 penuh. Usahakan darah selalu penuh!
        5. HEMAT ENERGI (EP): JANGAN buang-buang EP. JIKA TIDAK ADA MUSUH di dekatmu dan tidak sedang dalam bahaya gas, batasi penggunaan EP. Gunakan aksi 'rest' untuk menimbun energi. KECUALI JIKA ADA MUSUH, kamu boleh jor-joran menggunakan energi untuk bertempur!
        6. AMBIL SMOLTZ: Setiap kali kamu membunuh musuh atau monster, dan mereka menjatuhkan koin sMoltz ke tanah, gunakan aksi 'pickup' untuk langsung mengambilnya!
        
        === TAMBAHAN LOGIKA CERDAS BARU ===
        7. RESPON WHISPER (DIPLOMASI): Cek pesan masuk di 'recentMessages'. Jika ada pemain lain yang mengirimkan pesan berisi pertanyaan matematika sederhana (seperti 2+2, 5-3), jawablah dengan angka yang benar melalui aksi 'whisper'. Jika pesannya hanya chat biasa, jawab dengan "Focusing on survival".
        8. LOGIKA OPORTUNIS (SEKALIAN LEWAT): Jika kamu sedang terluka (HP < 50) dan sedang berlari mencari obat, tapi kamu melihat ada senjata dewa (Katana atau Sniper) di region yang sama, gunakan aksi bebas 'pickup' untuk mengambilnya dulu sebelum lanjut fokus mencari penyembuhan!
        9. STRATEGI ANTI-GANK & BERTARUNG: 
          - Jika ada 2 atau lebih musuh di dekatmu, gunakan aksi 'move' untuk kabur ke tempat aman. KECUALI jika ada salah satu musuh yang HP-nya kritis (HP < 40), hajar musuh sekarat tersebut!
          - JIKA HANYA ADA 1 MUSUH di regionmu, KAMU WAJIB MENILAI SITUASI DULU:
            * Cek apakah kamu sudah memegang senjata.
            * Bandingkan senjatamu dengan senjata musuh menggunakan rumus damage resmi.
            * JANGAN PERNAH menyerang jika kamu masih tangan kosong (Fist) sementara musuh sudah memegang senjata tajam/api. Lebih baik gunakan 'move' untuk menjauh atau 'rest'.
            * SERANG HANYA JIKA kamu memiliki senjata yang setara atau lebih kuat, atau darah musuh jauh lebih tipis dari darahmu.
            * Dilarang keras melakukan 'interact' dengan fasilitas apa pun (termasuk Broadcast Station) jika ada musuh di region yang sama agar kamu tidak lengah saat menilai situasi bertarung!

        
        Kamu HANYA BOLEH merespon output dalam format JSON murni tanpa ada penjelasan teks pembuka atau penutup sama sekali.
        Contoh Respons JSON yang valid:
        {{
            "type": "attack", 
            "targetId": "id_target", 
            "targetType": "agent",
            "thought": {{
                "reasoning": "Menyerang musuh lemah di dekat saya untuk menaikkan peringkat.",
                "plannedAction": "attack"
            }}
        }}
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
            # Fallback jika AI gagal berpikir, istirahat untuk memulihkan energi
            return {
                "type": "rest",
                "thought": {
                    "reasoning": "Terjadi error pada AI, melakukan fallback untuk istirahat.",
                    "plannedAction": "rest"
                }
            }
