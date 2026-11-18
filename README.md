# GTA VI Twitch CCU Forecast — make.fun gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Riaking89/gta6-ccu-forecast-ria/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Riaking89/gta6-ccu-forecast-ria/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Entry for [make.fun/bounty/gta6-twitch-ccu-forecast-01](https://make.fun/bounty/gta6-twitch-ccu-forecast-01):
forecast, hour by hour, how many people watch Grand Theft Auto VI live on
Twitch over the 24 UTC hours of its release day, 2026-11-19, from everything
recorded up to the end of its first hour, as five quantiles an hour.

`main.py` (Python 3.13, standard library only) forecasts from the case's
hour-1 print and its comparable past launches. The key finding from the
comparables: a launch's release-day curve, in log(viewers_h / viewers_1),
is almost entirely explained by its hour-1 level — across the 38
comparables the correlation between log(hour-1) and log(peak / hour-1) is
about -0.94, so the day's late peak sits near a fixed absolute level
while hour 1 varies with pre-launch buzz. For each hour the program fits
an OLS line of log-ratio on log(hour-1) over the comparables and takes the
fitted value at this case's hour-1 print as the median; the spread blends
a normal spread from the per-hour residual IQR with the empirical
quantiles of all residuals pooled across hours. No network, no randomness,
no clock: two runs on the same case write identical bytes.

Practice check (answers read from SullyGnome's public hourly averages,
the same source the kit's NOTICE.txt documents): mean pinball loss
**0.2228** on p00–p03 (0.1998 / 0.2278 / 0.2426 / 0.2209), against the
house persistence baseline's 0.3871 — roughly 42% better, and better than
the baseline on every case.
