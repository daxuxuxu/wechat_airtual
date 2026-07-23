#!/usr/bin/env bash

# Run from the Resource2Skill repository after configuring .env.
python -m pip install -r requirements.txt
python -m playwright install chromium

python cli.py agent \
  --domain web \
  --task "Build a one-page landing site for a neighborhood arts nonprofit called Quartz. Warm hand-made editorial style; programs, impact, donation tiers, FAQ, footer. Save and STOP." \
  --model gpt-5.4 \
  --reasoning low \
  --max-iter 40
