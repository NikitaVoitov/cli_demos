## Splunk Web

Splunk Web is at https://__SPLUNK_WEB_HOST__. Check pages with `playwright-cli`: `playwright-cli open <url>` starts a browser that is already signed in, so no login step is needed. A dashboard lives at `/en-US/app/search/<name>`. Panels take a few seconds to load; each panel is a region named "Visualization <panel title>", which `playwright-cli find` can match. Close the browser when you are done.
