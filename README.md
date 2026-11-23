# 🐰 Bunny: your offline AI desk buddy

Bunny lives on your old phone (Galaxy S10e) as a cute animated face and on your Windows PC as its brain.

**Three buddies**, each with its own face, voice and personality. Say a name to call that buddy, or tap 🎭 on the phone:

| Buddy | Face | Say |
|---|---|---|
| **Bunny** | a cute white bunny | "Bunny …" |
| **Pixel** | just two glowing eyes | "Pixel …" |
| **Robo** | a cheerful orange toy robot | "Robo …" |

You talk to it in Hindi, Hinglish or English:

- **"Bunny, Photoshop kholo"** opens Photoshop, **"Bunny, Chrome band karo"** closes Chrome (normally,
  so unsaved work is never lost)
- **"Bunny, awaaz badhao / kam karo / 40 pe karo"**, **"gaana roko"**, **"agla gaana"**
- **"Bunny, screenshot lo"**, **"computer lock karo"**, **"downloads kholo"**, **"YouTube kholo"**
- **"Bunny, Barbarik wali file dhundo"** finds a file by name in your folders and opens it
- **"Bunny, phone pe YouTube kholo"**, **"phone ki awaaz badhao"**, **"Bunny wapas aao"**
- **"Bunny, computer band karo"** asks "pakka?" first, then shuts down in 30 seconds (**"Bunny cancel karo"** stops it)
- **"Bunny, black hole kya hota hai?"** is answered by an AI model running **offline** on your PC
- **"Bunny, chup"** stops talking. **"Bunny, so jao"** sends Bunny to sleep. Tap the face to talk without saying the name.
- Speak English and it answers in English; speak Hindi or Hinglish and it answers in Hindi.

## Security

- **Everything is offline**: hearing (Whisper), thinking (Ollama) and the voice all run on your PC and phone.
- **Bunny cannot send, upload, share or delete files.** That code does not exist. Asking for it gets a polite "no".
- The AI only talks. Commands come from a fixed list, and anything the AI suggests is checked against that list.
- Bunny listens only on this PC (`127.0.0.1`). The phone reaches it through the USB cable, so nobody on your Wi-Fi
  can connect. Every request needs Bunny's secret token, and requests from websites are refused.
- The installer can lock Bunny out of the internet with Windows Firewall (recommended; Bunny never needs it).

## Install

1. Run **Bunny-Setup.exe**. Keep "Install Ollama" ticked if you don't have Ollama.
2. Bunny starts and downloads its AI brain **once** (gemma3:4b, about 3 GB). After that it works without internet.
3. **On the S10e**:
   - Settings ▸ About phone ▸ Software information ▸ tap **Build number** 7 times.
   - Settings ▸ Developer options ▸ turn on **USB debugging**.
   - Plug it into the PC. Tap **Allow** on the "Allow USB debugging?" message, and tick "Always allow".
   - Bunny's face opens in Chrome by itself. Tap the screen and allow the microphone.
4. No phone handy? Open **http://127.0.0.1:47865** on the PC to talk to Bunny with the PC microphone.

**Better Hindi voice on the phone:** Settings ▸ General management ▸ Text-to-speech ▸ choose **Google**, then download
the **Hindi (India)** voice.

## Settings

`%LOCALAPPDATA%\Bunny\settings.json`:

| Setting | What it does |
|---|---|
| `reply_language` | `auto` (same language you spoke), `hindi`, `english` or `hinglish` |
| `character` | `bunny`, `pixel` or `robo` |
| `llm_model` | `gemma3:4b` (default, 16 GB RAM). Use `gemma3:1b` for 8 GB RAM, or `gemma3:12b` for a strong PC with a graphics card |
| `whisper_model` | `small` (included) |
| `custom_apps` | your own apps, for example `{"my game": "D:\\Games\\game.exe"}` |

Restart Bunny after changing it.

## Coming next

- A Bunny app for the phone (APK) that works over Wi-Fi.
- **"Bunny, computer on karo"**: turns the PC on from the phone with Wake-on-LAN. This needs a LAN cable to the
  router and Wake-on-LAN turned on in the BIOS.
