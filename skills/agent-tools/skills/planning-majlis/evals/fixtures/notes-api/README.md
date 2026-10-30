# notes-api

A tiny notes API. `GET /` lists your notes, `POST /` with `{"text": "..."}` adds one.
Send your key in `X-Api-Key`. Notes live in memory; restarting the server loses them.
