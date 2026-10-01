# OJO Sentinel advert videos

Four spots, designed for muted autoplay: every line is on screen, and there's no audio track.

| File | Format | Length | Where |
|---|---|---|---|
| `ad1-we-see-everything-16x9` | 1920×1080 (16:9) | 30 s | YouTube, website, in-store screens, TV |
| `ad2-nobody-can-hide-9x16` | 1080×1920 (9:16) | 15 s | TikTok, Instagram Reels and Stories, WhatsApp Status |
| `ad3-runs-itself-9x16` | 1080×1920 (9:16) | 15 s | TikTok, Reels, Stories, WhatsApp Status |
| `ad4-pricing-1x1` | 1080×1080 (1:1) | 15 s | Facebook and Instagram feed, LinkedIn |

## Build

```sh
npm install playwright        # and ffmpeg on the PATH
node render.js ad1-we-see-everything-16x9.html     # → out/ad1-we-see-everything-16x9.mp4 (+ .jpg poster)
```

Each ad is an HTML page. Open it in a browser to preview it looping in real time. The renderer steps through it frame by frame at 30 fps and encodes H.264 MP4 (yuv420p, faststart), which the ad platforms accept. Timings are the `data-at="start end"` attributes, in seconds.

The fonts are Archivo and IBM Plex (SIL Open Font License, licences in `fonts/`).

## Scripts and optional voice-over

**1 · We see everything they ignore (30 s)**

| Time | On screen | Voice-over |
|---|---|---|
| 0–3 | Every shilling that leaks should have been your profit. | Every shilling that leaks should have been your profit. |
| 3–8 | The storekeeper said 10. The shelf sensors said 7. | The storekeeper said ten. The shelf said seven. |
| 8–13 | A truck leaves its route at 2 am. The fleet controller and the owner are called. | At two in the morning, a truck leaves its route. Your phone rings. |
| 13–18 | A cashier signs in with a colleague's login: face match 7%, REFUSED. | A borrowed login? Refused. |
| 18–23 | You will never owe KRA without knowing it first. | And you'll never owe KRA without knowing it first. |
| 23–27 | Every store. Every shilling. One screen. | Every store, every shilling, one screen. |
| 27–30 | OJO Sentinel. We see everything they ignore. From KES 10,000 a month, M-Pesa or card. | OJO Sentinel. We see everything they ignore. |

**2 · Nobody can hide it from you (15 s)**

| Time | On screen | Voice-over |
|---|---|---|
| 0–2.6 | "Everything's fine, boss." Is it? | "Everything's fine, boss." Is it? |
| 2.6–10 | Owner-direct alerts land on the phone: a tampered shipment, a short cash drawer, good stock written off, a refund spree. It isn't. Now you know. | (silence; the alerts are the story) |
| 10–13 | A manager tries to close the alert. REFUSED, and the owner is told. | Only you can close it. |
| 13–15 | No one can hide the truth from you. From KES 10,000 a month. | OJO Sentinel. |

**3 · Your business runs itself (15 s)**

| Time | On screen | Voice-over |
|---|---|---|
| 0–2.3 | Who runs your store when you're not there? | Who runs your store when you're not there? |
| 2.3–11 | 08:02 opens itself · 08:07 borrowed login refused · 13:10 power cut, generator on · 17:40 flour expiring · 20:05 shift reconciled · 20:06 alarm armed | OJO Sentinel does. |
| 11–15 | Your business runs itself. You just watch it grow. Premium, KES 50,000 a month. | Your business runs itself. You just watch it grow. |

**4 · Plans and pricing (15 s)**

| Time | On screen |
|---|---|
| 0–2.8 | Security, stock, cash and KRA. One subscription. |
| 2.8–10 | Basic KES 10,000 · Standard KES 30,000 · Premium KES 50,000 a month. Pay yearly: 2 months free. |
| 10–12.6 | Pay the way you pay: M-Pesa, Visa, Mastercard. Monthly or yearly, from your dashboard. |
| 12.6–15 | We see everything they ignore. Try the live demo. |

To add sound, lay a licensed music bed under the MP4s (or record the voice-over above) in any editor. The cuts land on the times in the tables.
