# 🛡️ AEGIS VEIL

> **A high-end, plausible-deniability steganography and secure cloud storage platform.**

AEGIS VEIL (formerly Stego-Cloud) is an advanced multi-tenant platform that hides encrypted files within innocent-looking, high-resolution images. Cloaked behind a beautifully crafted, immersive "Fallen Kingdom" photo gallery aesthetic, the system provides top-tier security including a dual-layered "Panic Mode" for absolute plausible deniability. 

---

## ✨ Key Features

- 🖼️ **Steganographic Cloud Storage**: Hide your sensitive files seamlessly inside standard image files without noticeable degradation.
- 🎭 **Panic Mode (Plausible Deniability)**: Dual-password authentication system. Entering a secondary "decoy" password opens an innocent gallery to satisfy unauthorized entities, keeping the true hidden vault completely invisible.
- 🏰 **Immersive 'Fallen Kingdom' UI/UX**: A dark, regal, and minimalistic dashboard interface ensuring that the application looks sophisticated and nothing like typical vault software.
- 🤝 **Joint Vaults**: Securely share and collaborate on hidden vaults with other users using granular access controls.
- ⚡ **Full-Stack Architecture**: Built on a high-performance **FastAPI** backend and a responsive, dynamic **Next.js** frontend.
- 🗄️ **Supabase Integration**: Robust handling of user authentication, reliable metadata tracking, and secure cloud storage.

---

## 🛠️ Technology Stack

* **Frontend**: Next.js (TypeScript), React, Modern Web CSS Aesthetics
* **Backend**: FastAPI (Python), Advanced Python steganography/crypto tools
* **Database & Auth**: Supabase (PostgreSQL, JWT-based Auth)

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v16+)
- Python (3.9+)
- Supabase Project (Database + Auth enabled)

### 1. Repository Setup
```bash
git clone https://github.com/rohiitx94/AEGIS-VEIL.git
cd AEGIS-VEIL
```

### 2. Backend Initialization
```bash
# Create and activate a virtual environment
python -m venv venv
# On Windows: venv\Scripts\activate
# On Unix or MacOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
*Ensure you create a `.env` file using `.env.example` as a template with your Supabase credentials.*

Start the backend API server:
```bash
uvicorn api.main:app --reload
```

### 3. Frontend Initialization
```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:3000` to access the true application interface.

---
*Developed with an uncompromising focus on absolute privacy, structural deception, and aesthetic excellence.*
