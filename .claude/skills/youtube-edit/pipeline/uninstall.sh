#!/bin/bash
# uninstall.sh: stop watching the inbox. Leaves every video folder, the inbox and the scripts alone.
LABEL="com.youtube-edit.inbox"
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 && echo "stopped $LABEL" || echo "$LABEL was not loaded"
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist" "$HOME/.local/bin/yt"
