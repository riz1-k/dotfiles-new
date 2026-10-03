#!/usr/bin/env bash
# Claude Code status line: one plain line.
# left: model - effort            right: ctx │ cache TTL │ misses │ 5h │ 7d

export LC_ALL=C.UTF-8  # so ${#var} counts characters, not bytes
input=$(cat)
US=$'\x1f'

IFS=$US read -r model effort fast think ctx_pct ctx_size cache_warm cache_exp cache_obs hit miss \
  five seven < <(
  jq -r '[
    .model.display_name,
    .effort.level,
    .fast_mode,
    .thinking.enabled,
    .context_window.used_percentage,
    .context_window.context_window_size,
    .prompt_cache.warm,
    .prompt_cache.expires_at,
    .prompt_cache.caching_observed,
    .prompt_cache.hit_ratio,
    .prompt_cache.misses,
    .rate_limits.five_hour.used_percentage,
    .rate_limits.seven_day.used_percentage
  ] | map(if . == null then "" else tostring end) | join("\u001f")' <<<"$input"
)

SEP="  │  "
lhs="$model"
rhs=""
add() { rhs+="${rhs:+$SEP}$1"; }

# effort (+ fast / no-thinking flags)
if [ -n "$effort" ]; then
  e="$effort"; [ "$fast" = "true" ] && e="$e ⚡"; [ "$think" = "false" ] && e="$e (no think)"
  lhs+=" - ${e}"
fi

# context: percent + window size
if [ -n "$ctx_pct" ]; then
  p=$(printf '%.0f' "$ctx_pct")
  size=""; [ -n "$ctx_size" ] && size=" of $(awk -v s="$ctx_size" 'BEGIN{ printf (s>=1000000)?"%.0fM":"%.0fk", (s>=1000000)?s/1000000:s/1000 }')"
  add "ctx ${p}%${size}"
fi

# prompt cache: countdown to cold
if [ "$cache_obs" = "true" ]; then
  left=$(( ${cache_exp%.*} - $(date +%s) )) 2>/dev/null
  if [ "$cache_warm" = "true" ] && [ -n "$cache_exp" ] && [ "$left" -gt 0 ]; then
    if   [ "$left" -ge 3600 ]; then t="$((left/3600))h$(( (left%3600)/60 ))m"
    elif [ "$left" -ge 60 ];   then t="$((left/60))m$(printf '%02d' $((left%60)))s"
    else t="${left}s"; fi
    h=""; [ -n "$hit" ] && h=" $(awk -v h="$hit" 'BEGIN{printf "%.0f%%", h*100}')"
    add "cache ${t}${h}"
  else
    add "cache cold"
  fi
fi

# cache misses (only when there are any)
[ "${miss:-0}" -gt 0 ] && add "miss ×${miss}"

# rate limits (subscribers only)
[ -n "$five" ]  && add "5h $(printf '%.0f' "$five")%"
[ -n "$seven" ] && add "7d $(printf '%.0f' "$seven")%"

# right-align the metrics; fall back to a plain join if the width is unknown or too tight
pad=$(( ${COLUMNS:-0} - ${#lhs} - ${#rhs} - 4 ))
if [ -z "$rhs" ]; then
  printf '%s' "$lhs"
elif [ "$pad" -ge 4 ]; then
  printf '%s%*s%s' "$lhs" "$pad" '' "$rhs"
else
  printf '%s%s%s' "$lhs" "$SEP" "$rhs"
fi
