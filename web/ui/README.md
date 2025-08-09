# Future Web UI Scaffold

This directory will host a lightweight static web UI for browsing Radar outputs:
- Tag filters
- Full text + semantic search (client hits a small local server or prebuilt index)
- Dossier navigation & update timeline

Planned structure:
```
web/ui/
  index.html      # entry point
  js/
    app.js        # SPA logic (future)
  css/
    app.css       # overrides + theme
```

Not yet implemented; included now to reserve structure and allow incremental PRs.