<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.carhunter.scheduler</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>__PROJECT_DIR__/local/run.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>__PROJECT_DIR__</string>

    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key><integer>0</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key><integer>6</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key><integer>12</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key><integer>18</integer>
            <key>Minute</key><integer>0</integer>
        </dict>
    </array>

    <key>StandardOutPath</key>
    <string>__PROJECT_DIR__/.tmp/run.log</string>

    <key>StandardErrorPath</key>
    <string>__PROJECT_DIR__/.tmp/run.err</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
