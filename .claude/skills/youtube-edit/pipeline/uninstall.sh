#!/bin/bash
# uninstall.sh: stop watching the inbox (and the render inbox, on the home Mac). Leaves every video folder, both
# inboxes and the scripts alone.
for LABEL in com.youtube-edit.inbox com.youtube-edit.render-host; do
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 && echo "stopped $LABEL" || echo "$LABEL was not loaded"
  rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
done
rm -f "$HOME/.local/bin/yt"
