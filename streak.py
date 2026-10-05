name: Update streak card

on:
  schedule:
    - cron: "15 */6 * * *"   # every 6 hours
  workflow_dispatch:

permissions:
  contents: write

jobs:
  streak:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v5

      - name: Generate streak card
        env:
          GH_LOGIN: ${{ github.repository_owner }}
          GH_TOKEN: ${{ secrets.METRICS_TOKEN }}
        run: python streak.py

      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add assets/streak.svg
          git diff --cached --quiet || git commit -m "chore: update streak card"
          git push
