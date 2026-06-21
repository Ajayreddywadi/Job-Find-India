import requests, re, html, textwrap

def clean_html(raw):
    decoded = html.unescape(raw or '')
    no_tags = re.sub(r'<[^>]+>', ' ', decoded)
    return re.sub(r'\s+', ' ', no_tags).strip()

def truncate(text, max_chars=300):
    return textwrap.shorten(text, width=max_chars, placeholder='...')

keyword = 'react developer'

# Test RemoteOK
print("=== RemoteOK ===")
r = requests.get('https://remoteok.com/api', timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
data = r.json()
jobs = [j for j in data if isinstance(j, dict) and j.get('position')]
print(f'Total raw jobs from API: {len(jobs)}')

# Show first 5 job titles
for j in jobs[:5]:
    print(f"  title: {j.get('position','')} | tags: {j.get('tags',[][:3])}")

# Test keyword matching tiers
tokens = [t for t in re.split(r'[\s\-_/().]+', keyword.lower()) if len(t) > 2]
primary = max(tokens, key=len) if tokens else ''
print(f"\nTokens: {tokens}, Primary: {primary!r}")

matched_exact = matched_all = matched_primary = 0
for raw in jobs:
    pos   = raw.get('position', '')
    comp  = raw.get('company', '')
    tags  = raw.get('tags', []) or []
    desc  = truncate(clean_html(raw.get('description', '')))
    text  = f"{pos} {comp} {' '.join(tags)} {desc}".lower()
    if keyword.lower() in text:
        matched_exact += 1
    if all(t in text for t in tokens):
        matched_all += 1
    if primary and primary in text:
        matched_primary += 1

print(f"Exact phrase match:  {matched_exact}")
print(f"All-words match:     {matched_all}")
print(f"Primary-word match:  {matched_primary}")

# Test Remotive
print("\n=== Remotive ===")
r2 = requests.get('https://remotive.com/api/remote-jobs', params={'search': 'react', 'limit': 10}, timeout=15)
data2 = r2.json()
jobs2 = data2.get('jobs', [])
print(f"Jobs returned for search=react: {len(jobs2)}")
for j in jobs2[:3]:
    print(f"  {j.get('title','')} | {j.get('company_name','')} | loc: {j.get('candidate_required_location','')}")

# Test Arbeitnow
print("\n=== Arbeitnow ===")
r3 = requests.get('https://www.arbeitnow.com/api/job-board-api', timeout=15)
data3 = r3.json()
jobs3 = data3.get('data', [])
print(f"Total Arbeitnow jobs: {len(jobs3)}")
matched_primary_arb = 0
for j in jobs3:
    text = f"{j.get('title','')} {j.get('description','')[:200]}".lower()
    if primary and primary in text:
        matched_primary_arb += 1
print(f"Primary-word match for {primary!r}: {matched_primary_arb}")
