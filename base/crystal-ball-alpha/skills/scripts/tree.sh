#!/usr/bin/env bash
# Crystal Ball Skill Tree
# Run: bash .agent/skills/crystal-ball/scripts/tree.sh
#
# Shows the full skill tree with domains, subdomains, and process files.

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CB_DIR="$SKILL_DIR/cb_skills"

echo "🔮 Crystal Ball Skill Tree"
echo "=========================="
echo ""

if [ ! -d "$CB_DIR" ]; then
  echo "No cb_skills directory found at $CB_DIR"
  exit 1
fi

for domain in "$CB_DIR"/*/; do
  [ -d "$domain" ] || continue
  domain_name=$(basename "$domain")
  echo "📂 $domain_name/"
  
  for subdomain in "$domain"*/; do
    [ -d "$subdomain" ] || continue
    subdomain_name=$(basename "$subdomain")
    echo "  📁 $subdomain_name/"
    
    for process in "$subdomain"*.md; do
      [ -f "$process" ] || continue
      process_name=$(basename "$process" .md)
      # Extract first line after the heading as description
      desc=$(grep -m1 '^>' "$process" 2>/dev/null | sed 's/^> //')
      if [ -n "$desc" ]; then
        echo "    📄 $process_name — $desc"
      else
        echo "    📄 $process_name"
      fi
    done
  done
  echo ""
done

# Summary
total_domains=$(find "$CB_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
total_subdomains=$(find "$CB_DIR" -mindepth 2 -maxdepth 2 -type d | wc -l | tr -d ' ')
total_processes=$(find "$CB_DIR" -name "*.md" -type f | wc -l | tr -d ' ')
echo "─────────────────────────"
echo "📊 $total_domains domains · $total_subdomains subdomains · $total_processes processes"
