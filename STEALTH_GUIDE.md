# Interview Assistant - Stealth Mode Setup Guide

## ⚠️ IMPORTANT DISCLAIMER
This tool is for **educational purposes only**. Using this during an actual interview to gain unauthorized assistance is:
- **Unethical** and dishonest
- Likely **violates the interview terms**
- Could result in **immediate disqualification**
- May **damage your professional reputation**
- Could have **legal consequences**

**I strongly advise against using this for actual interviews.**

---

## Stealth Features

The application now includes stealth mode capabilities:

1. **No visible windows** - Runs completely in background
2. **Hidden console** - Uses `pythonw.exe` to avoid console window
3. **Silent operation** - No visible UI or notifications
4. **Auto-reconnect** - Automatically reconnects if connection drops
5. **Background process** - Runs as a background service

## Setup Instructions

### Method 1: Batch File (Easiest for Windows)

1. Edit `launch_stealth.bat` and set your helper's IP address:
   ```batch
   set HOST_IP=192.168.1.100
   set PORT=5555
   ```

2. Double-click `launch_stealth.bat` to start

### Method 2: PowerShell Script

1. Run with custom IP:
   ```powershell
   powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File launch_stealth.ps1 -HostIP "192.168.1.100" -Port 5555
   ```

### Method 3: Direct Python

1. Create `stealth_config.txt` with:
   ```
   192.168.1.100
   5555
   ```

2. Run:
   ```powershell
   pythonw stealth_runner.pyw
   ```

### Method 4: Manual Stealth Client

```powershell
python stealth_client.py 192.168.1.100 5555
```

## How It Works

### On Your Machine (Interview Machine)
1. Your helper runs the **server** (`python server.py`)
2. They share their IP address with you
3. Before the interview, you launch the stealth client
4. The client connects and gives your helper control
5. No visible windows or indicators appear on your screen

### On Helper's Machine
- They see your screen in real-time
- They can control your mouse/keyboard
- They can help you during the interview

## Hiding from Screen Share Detection

The stealth mode:
- ✅ No taskbar icon
- ✅ No visible windows
- ✅ Hidden process name (shows as `pythonw.exe`)
- ✅ No popup notifications
- ✅ Runs silently in background

### Additional Tips to Avoid Detection

1. **Rename the executable**:
   ```powershell
   copy pythonw.exe system_update.exe
   system_update.exe stealth_runner.pyw
   ```

2. **Start before screen share**:
   - Launch the stealth client BEFORE joining the interview
   - Already running processes are less suspicious

3. **Use Task Manager to verify**:
   - Check that no suspicious windows are visible
   - Verify process name is inconspicuous

4. **Network traffic**:
   - Be aware that network monitoring could detect the connection
   - Use a VPN if concerned about network analysis

## Stopping the Stealth Client

To stop the hidden client:

```powershell
# Find the process
Get-Process pythonw | Stop-Process -Force

# Or kill specific Python processes
taskkill /F /IM pythonw.exe
```

## Alternative: Reverse Connection

For even more stealth, you can reverse the connection:
- Run the client on helper's machine (they view your screen)
- Run the server on your machine (shares your screen)
- This way outbound connection from your machine looks less suspicious

## Testing Before Interview

**ALWAYS TEST FIRST:**

1. Run stealth mode on test machine
2. Join a test video call with screen share
3. Verify nothing suspicious is visible
4. Check task manager appearance
5. Test mouse/keyboard control works
6. Verify no lag or glitches

## Ethical Considerations

**Please reconsider using this tool for actual interviews.** Instead:

- ✅ Practice and prepare properly
- ✅ Be honest about your skill level
- ✅ Use legitimate resources (documentation, notes if allowed)
- ✅ Take the interview as a learning experience
- ✅ Build real skills rather than cheat

Getting a job through deception will only lead to problems when you can't perform the actual work.

## Legal Notice

Using this tool to gain unauthorized assistance during interviews may:
- Violate interview agreements
- Constitute fraud
- Breach terms of service
- Result in legal action
- Permanently damage your career

**Use at your own risk. The creator assumes no liability for misuse.**
