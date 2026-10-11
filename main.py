"""
HubSpot - Leads Assigned + Meetings Completed + Calls + Sales + New
Business + Renewals + Old-Lead Sales + Derived Ratios, by Owner
(Weekly -> Monthly -> Yearly, collapsible, ALL METRICS in ONE sheet tab)
-----------------------------------------------------------------------------
This is the previously-working Leads/Meetings/Calls/Sales script, extended
additively with 5 new raw metric blocks and 4 derived ratio blocks. NONE of
the existing Leads, Meetings, Calls, or combined Sales #/$ logic has been
modified - every function that produced those blocks before produces
bit-for-bit the same result now. New behavior is either brand new functions,
or small OPTIONAL, default-None parameters added to a few deal-fetch
functions (build_deal_filters, fetch_deal_count_probe,
_fetch_deal_tallies_single, fetch_deal_tallies, fetch_deal_period_live) so
the new Old-Lead-Sales block can add one extra filter - existing call sites
for those functions don't pass the new parameter, so their behavior is
unchanged.

=============================================================================
FIX APPLIED IN THIS COPY (round 6) - confined to deal-level SOURCE property
resolution and the AI Sales branch list; every metric's fetch logic, the
period tree, the row builders, and all Sheets formatting are untouched:

  G. The run died at resolve_deal_property_exact_label(..., "Source*", ...)
     with "multiple deals properties matched ['source']" and a list of 25
     candidates. Cause: "Source*" is a CONTACT property label in this
     portal (it resolves fine there to leconnex_source), but there is NO
     deal property with that label, so the resolver fell back to a
     substring match on ["source"] - which matches Deal Source, Latest
     Traffic Source, Original Traffic Source, Record creation source,
     Source Object ID, and 20 more. It correctly refused to guess.
     FIX: the real deal-level source property is "Deal Source "
     (internal: deal_source), taken from that error's own candidate list,
     and is now given directly via DEAL_SOURCE_PROPERTY_OVERRIDE - the
     same manual-override pattern already used by INCOME_PROPERTY_OVERRIDE
     for the same reason (auto-resolution genuinely cannot disambiguate).
     A new verify_deal_property_exists() fetches the override and prints
     its real label + field type, so a typo'd/deleted internal name 404s
     immediately instead of silently returning 0 for a whole block.

  H. The very next line resolved a deal-level "Inferred Landing Page" the
     same fatal way, and would have killed the run again if that property
     only exists on contacts in this portal. FIX: it now resolves through
     a new NON-FATAL resolver (resolve_deal_property_optional) which
     returns None instead of exiting, and Block 28 (AI Sales #) adds its
     second OR-branch only if that property actually resolved - printing a
     loud under-count warning if it didn't. When both properties resolve,
     Block 28's branch list is byte-for-byte identical to before.
=============================================================================
FIXES APPLIED IN THIS COPY (round 3) - all confined to the round-2 contact
search engine; every earlier block is untouched:

  A. HubSpot rejected the Google Leads / AI Leads queries with
     "too many filters per filter group (count: 7, max allowed: 6)".
     Each branch was carrying 7 AND'd filters:
       1 owner HAS_PROPERTY, 2 create-date GTE, 3 create-date LTE,
       4 firstname NOT_CONTAINS_TOKEN, 5 email NOT_CONTAINS_TOKEN,
       6 contact_status NOT_IN, 7 source CONTAINS_TOKEN.
     FIX: the GTE+LTE pair is collapsed into ONE inclusive BETWEEN filter
     for those two builders only (see build_create_date_range_filters,
     compact=True), taking each branch to exactly 6 filters. BETWEEN is
     inclusive of both bounds, so the matched record set is identical to
     the GTE/LTE pair used by every other block. Every other round-2
     builder is at 4 filters and is left on the original GTE/LTE form.

  B. _rewrite_date_bounds() only knew how to rewrite GTE/LTE filters, so a
     BETWEEN-form branch that tripped the 10k-cap splitter would have
     silently kept its ORIGINAL full date range in both halves (double-
     counting). FIX: it now rewrites BETWEEN's value/highValue too.

  C. fetch_contact_records_multi_branch() now validates every branch
     against MAX_FILTERS_PER_GROUP BEFORE issuing a request, so any future
     builder that grows past the cap fails immediately with the offending
     filter list printed, instead of a bare 400 mid-run after 20+ minutes
     of fetching.

  D. resolve_contact_property_option_values() now de-duplicates its
     resolved values. This portal has ONE combined Contact Status* option
     labeled "Duplicate, Don't Work", so both keyword groups
     (["duplicate"] and ["don't work"]) resolved to the same value and it
     was being sent to NOT_IN twice. Harmless but wasteful/confusing in
     logs; the exclusion itself was already correct.
=============================================================================

FIX APPLIED IN THIS COPY (round 4) - confined to the two blocks named
below; every other block is untouched:

  E. AI/ChatGPT Leads and Google Leads Assigned - replaced the earlier
     GUESSED filter logic (4 case variants of "Google", 6 guessed variants
     of "ChatGPT"/"OpenAI", plus firstname/email/contact-status exclusion
     conditions that were never actually part of either real HubSpot
     view) with the EXACT filters confirmed directly against the real
     HubSpot saved views/screenshots:
       - Google Leads Assigned:  Source* contains exactly "Google"
         (single condition, single branch).
       - AI/ChatGPT Leads:  (Source* contains exactly "AI"  AND  Date
         Created in period)  OR  (Inferred Landing Page contains exactly
         "chatgpt"  AND  Date Created in period) - two branches, each
         carrying its own copy of the date-range filter (confirmed by
         screenshot: both OR'd groups include the Date Created condition
         individually, not just once at the top level).
     Neither of the real views filters on owner-assigned, firstname,
     email, or Contact Status* - those conditions have been removed for
     these two blocks only. See build_google_leads_branches /
     build_ai_leads_branches below.

  F. Total New Lead (no appt) - the filter previously implemented here
     was IDENTICAL to the Appt Set filter (Appointment Set Calculation
     EQUAL TO 1), which is backwards for a "no appt" metric and was
     badly undercounting (233 vs. a real report total of 566 for the
     same period). Confirmed via the real HubSpot report
     (report 108263989): Classic List Membership is none of "imported"
     AND Date Created in period AND Appointment Set Calculation is NOT
     EQUAL TO 1. Fixed to NEQ. See build_new_lead_no_appt_branches below.
=============================================================================

NEW BLOCKS IN THIS VERSION:

  1. NEW BUSINESS # / $  - same closed-won-date property, amount property,
     owner property, and timezone as your existing combined Sales #/$
     block, but scoped to ONLY the "Closed won" stage (not "Renewal -
     Closed won"). Resolved via an EXACT label match on that one stage
     within the Sales Pipeline (resolve_deal_stage_by_exact_label) - a
     brand new function, so the existing resolve_closed_won_dealstages()
     (which intentionally returns BOTH stage IDs together for the
     existing Sales block) is untouched.

  2. RENEWALS # / $  - identical mechanism, scoped to ONLY "Renewal -
     Closed won".

  3. SALES FROM OLD LEADS (60+ DAYS) # / $  - same scope as the existing
     combined Sales block (both closed-won stages), with one extra filter
     on the deal property old_lead__60__days__ = its "Yes" option. The
     "Yes" option's real internal enum value is resolved by label
     (resolve_old_lead_yes_value), not hardcoded, matching this script's
     existing philosophy for meeting outcome. ASSUMPTION: this block
     counts a deal regardless of new-business/renewal status - the
     property is about lead age, not deal type. Flag if you actually want
     it scoped to New Business only.

  4. DERIVED RATIOS (Avg Sale $, Sales/Leads (non-renewals),
     Meetings/Leads, Sales/Meetings)  - pure division on totals/values
     ALREADY fetched by the blocks above - these make ZERO additional
     HubSpot API calls. Computed by a new generic function,
     build_ratio_rows(), period-by-period and (where the two source
     blocks share a compatible owner-key space) per owner too. A blank
     or zero denominator always renders as a blank cell, never a divide-
     by-zero error.
       - Avg Sale $                 = Sales $  / Sales #      (existing combined Sales block - new business + renewals)
       - Sales/Leads (non-renewals) = New Business # / Total Leads Assigned
       - Meetings/Leads             = Total Meetings Completed / Total Leads Assigned
       - Sales/Meetings             = New Business # / Total Meetings Completed
     CAVEAT: Sales/Leads and Meetings/Leads divide by owner name across
     two blocks whose owner names come from DIFFERENT sources - the Leads
     block's names come from a free-text HubSpot contact property, while
     Sales/Meetings names come from the real Owners API. If a rep's name
     is formatted differently between the two (nickname, middle initial,
     etc.) that owner's per-owner ratio cell will be blank even though
     the Total row is still correct (Total row totals are is summed
     independently and doesn't depend on owner-name matching).

Everything else - period tree construction, week/month grouping rules,
collapsible column groups, live-fetch-no-caching policy, formatting,
10k-result-cap splitting, retry/backoff - is unchanged and shared by every
block, old and new.

SETUP: same as before -
  export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxx"
  export GOOGLE_SERVICE_ACCOUNT_JSON='{...full service account json...}'
  pip install requests pytz gspread google-auth --break-system-packages

USAGE:
  python leads_meetings_calls_by_owner.py

-----------------------------------------------------------------------------
FIX APPLIED IN AN EARLIER COPY (kept - see resolve_closed_won_date_property
below): some portals have BOTH a "Closed won date" property AND a "Closed
Won Date (Internal)" property. The old CLOSED_WON_DATE_LABEL_KEYWORDS
substring match ("closed won date") matched both labels and exited with a
"multiple properties matched" error. resolve_closed_won_date_property does
an EXACT (not substring) label match first - same pattern used by
resolve_amount_property for the analogous "Amount" vs "Amount in company
currency" ambiguity - and only falls back to the old substring resolver if
no exact match is found.
-----------------------------------------------------------------------------
"""

import os
import sys
import json
import time
import calendar
import threading
from functools import partial
import requests
from datetime import datetime, timedelta, timezone as dt_timezone
from concurrent.futures import ThreadPoolExecutor
import pytz
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SEARCH_ENDPOINT = "https://api.hubapi.com/crm/v3/objects/contacts/search"
PROPERTIES_ENDPOINT = "https://api.hubapi.com/crm/v3/properties/contacts"
OWNERS_ENDPOINT = "https://api.hubapi.com/crm/v3/owners"

NO_VALUE_LABEL = "(No value)"
OTHERS_LABEL = "Other (MMs)"

# HubSpot's Search API hard-caps a single query at 10,000 retrievable
# results, AND the 'total' field itself appears to be capped at that same
# number once a range is at/over it (a range that truly matches 24,000
# records can report total=10000, not the real count) - so a raw total
# near the cap can't be trusted on its own, not just pagination. Kept well
# under the real 10,000 for safety margin. Used by both the Leads block
# (2025's full-year total is already ~9,013 and climbing - this was on
# track to hit the same wall within months) and the Meetings/Calls blocks
# (Calls volume already exceeds it on Month/Year Total & YTD columns).
MAX_RESULTS_PER_QUERY = 9500

# FIX (A/C): HubSpot rejects any single filterGroup carrying more than this
# many filters - confirmed live by the portal's own error message
# ("too many filters per filter group (count: 7, max allowed: 6)"). Every
# branch built by the round-2 contact-search engine is validated against
# this BEFORE a request is issued (see fetch_contact_records_multi_branch),
# so a builder that grows past the cap fails loudly and immediately rather
# than with a bare 400 partway through a long run.
MAX_FILTERS_PER_GROUP = 6

ROSTER_WINDOW_DAYS = 90

# A calendar month is assigned at most 5 Sun-Sat weeks (majority-of-days
# rule can never produce more), so this comfortably covers "all the weeks
# in a month at once" with a little headroom. Each concurrent fetch still
# goes through the same request_with_retry() 429/5xx backoff as before -
# concurrency just means more requests can be in flight, not that retries
# stop happening.
WEEK_FETCH_CONCURRENCY = 6

OWNER_FILTER_PROPERTY_LABEL_KEYWORDS = ["contact owner on first assigned date"]
OWNER_DISPLAY_PROPERTY_LABEL_KEYWORDS = ["first assigned contact owner", "by name"]

CREATE_DATE_PROPERTY = "leconnex_create_date"  # "Date Created* [DO NOT CHANGE]" - UTC date-only

TIMEZONE = "America/New_York"

ANCHOR_START_YEAR = 2024
ANCHOR_START_MONTH = 4  # April 2024

SPREADSHEET_ID = "1lvrcN0uSiO_62gJX-r6SpwSd8Px1rx7IUbzmgIq6n14"
SHEET_TAB_NAME = "Master Metric Sheet"

TOTAL_ROW_LABEL = "Total Leads Assigned"

# --- Meetings Completed / Calls config --------------------------------------

# See docstring point 3 above - flip to "UTC" if a spot-check against the
# HubSpot dashboard shows a day-boundary mismatch.
# Confirmed per-metric: Meetings uses account-local time (matches the EDT
# display in that report), Calls uses UTC (matches the UTC display in that
# report) - these are genuinely different, not a display-only quirk.
MEETINGS_TIMEZONE = "America/New_York"
CALLS_TIMEZONE = "UTC"

ACTIVITY_DATE_LABEL_KEYWORDS = ["activity date"]
ACTIVITY_OWNER_LABEL_KEYWORDS = ["activity assigned to"]
ACTIVITY_OWNER_LABEL_FALLBACK_KEYWORDS = ["owner"]
MEETING_OUTCOME_LABEL_KEYWORDS = ["meeting outcome"]
MEETING_OUTCOME_TARGET_LABEL = "completed"

MEETINGS_TOTAL_ROW_LABEL = "Total Meetings Completed"
CALLS_TOTAL_ROW_LABEL = "Total Calls"

# --- Sales # / Sales $ config ------------------------------------------

# Confirmed: "Closed won date" uses UTC, matching the Calls block (not
# Meetings' America/New_York) - the report screenshot showed no timezone
# annotation at all, unlike Meetings/Calls which explicitly showed
# EDT/UTC, so this was confirmed directly rather than inferred.
SALES_TIMEZONE = "UTC"

# dealstage is a fixed HubSpot system property - its internal name can't
# be changed even if the property gets relabeled, so unlike everything
# else in this script it's safe to hardcode rather than resolve by label.
DEALSTAGE_PROPERTY = "dealstage"

# Both "Closed won" and "Renewal - Closed won" are stages INSIDE the same
# "Sales Pipeline" pipeline (per the report screenshot, both options were
# suffixed "(Sales Pipeline)") - resolved via the Pipelines API (not the
# generic Properties API) so both distinct closed-won-type stages come
# back from one substring match, without hardcoding stage IDs or assuming
# there are exactly two.
DEAL_PIPELINE_LABEL_KEYWORDS = ["sales pipeline"]
CLOSED_WON_STAGE_LABEL_KEYWORDS = ["closed won"]

CLOSED_WON_DATE_LABEL_KEYWORDS = ["closed won date"]
DEAL_OWNER_LABEL_KEYWORDS = ["deal owner"]

SALES_COUNT_TOTAL_ROW_LABEL = "Total Sales #"
SALES_DOLLAR_TOTAL_ROW_LABEL = "Total Sales $"

# --- NEW: New Business / Renewals split -------------------------------------
# Same closed-won-date property, amount/owner properties, and SALES_TIMEZONE
# as the existing combined Sales #/$ block above - the only difference is
# which SINGLE dealstage is included, instead of both. Resolved by EXACT
# label match on the individual stage (resolve_deal_stage_by_exact_label,
# a new function - NOT the existing resolve_closed_won_dealstages(), which
# intentionally returns both stage IDs together for the block above) so
# New Business and Renewals never double-count or overlap with each other
# or with anything in the existing Sales block.
NEW_BUSINESS_STAGE_EXACT_LABEL = "closed won"
RENEWAL_STAGE_EXACT_LABEL = "renewal - closed won"

NEW_BUSINESS_COUNT_TOTAL_ROW_LABEL = "Total New Business #"
NEW_BUSINESS_DOLLAR_TOTAL_ROW_LABEL = "Total New Business $"
RENEWALS_COUNT_TOTAL_ROW_LABEL = "Total Renewals #"
RENEWALS_DOLLAR_TOTAL_ROW_LABEL = "Total Renewals $"

# --- NEW: Sales from Old Leads (60+ Days) -----------------------------------
# Scoped to ALL closed-won deals (both "Closed won" and "Renewal - Closed
# won" stages - same scope as the existing combined Sales #/$ block),
# filtered additionally by the "Old Lead (60+ Days)?" deal dropdown.
# ASSUMPTION: counts a deal regardless of new-business/renewal status,
# since the property is about how old the originating lead was, not deal
# type - flag if you want this scoped to New Business only instead.
OLD_LEAD_PROPERTY = "old_lead__60__days__"  # internal name given directly - not resolved by label
OLD_LEAD_YES_LABEL_KEYWORDS = ["yes"]  # adjust if the dropdown's "yes" option isn't literally labeled "Yes"

OLD_LEAD_SALES_COUNT_TOTAL_ROW_LABEL = "Total Sales from Old Leads (60+ Days) #"
OLD_LEAD_SALES_DOLLAR_TOTAL_ROW_LABEL = "Total Sales from Old Leads (60+ Days) $"

# --- NEW: Derived ratio metrics ---------------------------------------------
# Pure math on totals/values already fetched by the blocks above - NO
# additional HubSpot queries. See docstring point 4 for the exact formulas
# and the owner-name-matching caveat on the two Leads-denominator ratios.
AVG_SALE_ROW_LABEL = "Avg Sale $"
SALES_PER_LEAD_ROW_LABEL = "Sales/Leads (non-renewals)"
MEETINGS_PER_LEAD_ROW_LABEL = "Meetings/Leads"
SALES_PER_MEETING_ROW_LABEL = "Sales/Meetings"

# ---------------------------------------------------------------------------
# NEW (round 2): Google Leads / AI Leads / Organic Leads / Appt Set family /
# MM Recruits / Appt Set Show Rate config.
#
# Everything above this point is completely untouched - these are pure
# additions. The new blocks reuse the existing period tree, the existing
# fetch_metric_periods() walker, and the existing build_metric_rows() /
# build_ratio_rows() row builders wherever the shape fits (see the new
# "generic contact-search engine" functions further down for the parts
# that don't fit the existing Leads/Meetings/Calls fetch shape - mainly
# because several of these reports filter on a classic HubSpot LIST
# membership, which is not a contact property and can't be expressed as
# a Search API filter the way everything else in this script is).
# ---------------------------------------------------------------------------

# --- Google Leads / AI Leads / Organic Leads --------------------------------
# CONFIRMED (round 4, see FIX E above) directly against the real HubSpot
# saved views:
#   - Google Leads Assigned:  Source* contains exactly "Google"
#     (single condition - no case-variant OR, no owner/name/email/status
#     conditions - those were earlier guesses, now removed).
#   - AI/ChatGPT Leads:  (Source* contains exactly "AI" AND Date Created
#     in period)  OR  (Inferred Landing Page contains exactly "chatgpt"
#     AND Date Created in period).
GOOGLE_SOURCE_CONTAINS_VALUE = "Google"

AI_SOURCE_CONTAINS_VALUE = "AI"
INFERRED_LANDING_PAGE_EXACT_LABEL = "Inferred Landing Page"
INFERRED_LANDING_PAGE_CONTAINS_VALUE = "chatgpt"

SOURCE_PROPERTY_EXACT_LABEL = "Source*"

GOOGLE_LEADS_TOTAL_ROW_LABEL = "Total Google Leads Assigned"

AI_LEADS_TOTAL_ROW_LABEL = "Total AI/ChatGPT Leads Assigned"

ORGANIC_LEADS_TOTAL_ROW_LABEL = "Total Organic Leads Assigned (Google + AI/ChatGPT)"

# --- Appt Set / Appt Set High-Income / Appt Set Low-Income / New Lead
#     (no appt) / Appt Set Meetings Completed / Appt Set: Show Rate --------
APPOINTMENT_SET_CALC_EXACT_LABEL = "Appointment Set Calculation"
APPOINTMENT_SET_CALC_TARGET_VALUE = "1"
DATE_MET_WITH_EXACT_LABEL = "Date Met With (face-to-face)"

# FLAG - UNVERIFIED PROPERTY TYPE: "Income" is resolved by label (see
# resolve_contact_property_exact_label - point 2 of your instructions:
# reuse script 2's label-resolution pattern rather than hardcoding an
# internal name). The GTE/LTE filters below only work correctly if Income
# is a true NUMBER property. If it's actually a dropdown/enumeration of
# income BANDS (very common for lead-gen forms, e.g. "$50,000-$74,999"),
# GTE/LTE against a raw number won't match anything and both income
# blocks will silently return 0 every period. If your income property
# turns out to be an enumeration, tell me its option labels and I'll
# switch this to an IN/NOT_IN match on the specific band(s) instead.
INCOME_PROPERTY_EXACT_LABEL = "Income"

# FLAG - MANUAL OVERRIDE NEEDED: your portal has no property labeled
# exactly "Income", and 7 different candidates matched the substring
# "income" (Income for Zap In, JR Annual Income, Match's Preferred Income
# Range, Smartmatch Income, "What income range would you like your
# partner to be in?", "What is your income range?", Income Range) - auto-
# resolution can't safely guess between them, several are clearly about
# the PARTNER's desired income rather than the contact's own. Open the
# actual "Appt Set High Income (75k+)" report/filter in HubSpot, see which
# property its income filter uses, and paste its INTERNAL name here (the
# value in parentheses in the error message, e.g. "income_for_zap_in").
# Leave as None to keep attempting auto-resolution (which will keep
# erroring with the candidate list until this is set).
# ALSO CHECK: that property's field type. GTE/LTE (the 75k+ / 0-75k
# filters) only works if it's a true Number property - if it's actually a
# dropdown of income BANDS, tell me the option labels and I'll switch the
# high/low income filters to match specific bands via IN/NOT_IN instead.
INCOME_PROPERTY_OVERRIDE = "your_income_range"  # CONFIRMED via fill-rate check (42.58% fill vs. <7% for every other "income" candidate) AND via the live property-type check below: this is a Dropdown select ("enumeration"/"select") with real option values 0-75, 0-50, 50-100, 75-150, 100-150, 150-250, 250-500, 250+, 500-1M, 1M+ (plus a blank option). Verified live against your portal on the previous run - see verify_income_property_type() below.

# CONFIRMED band values (pulled live from your portal - see the error output
# from the previous run). These look like two overlapping band systems on
# the same property (one older/coarser: 0-50/50-100/100-150, one newer:
# 0-75/75-150/150-250/250-500/500-1M/1M+, plus a standalone "250+"), so the
# lists below are built from ALL bands that are UNAMBIGUOUSLY on one side
# of the $75k line - see INCOME_AMBIGUOUS_VALUES for the one that isn't.
INCOME_LOW_VALUES = ["0-75", "0-50"]                                    # fully below $75k
INCOME_HIGH_VALUES = ["75-150", "100-150", "150-250", "250-500", "250+", "500-1M", "1M+"]  # fully at/above $75k

# FLAG: "50-100" spans $50k-$100k, straddling the $75k line - there's no
# way to cleanly bucket it as strictly High or Low without more granular
# data than the dropdown gives us. It is DELIBERATELY EXCLUDED from BOTH
# INCOME_LOW_VALUES and INCOME_HIGH_VALUES, so a contact with this value
# won't be counted in either the High Income or Low Income block - meaning
# High + Low will UNDER-count vs. a hypothetical "everyone" total by
# however many contacts have exactly "50-100". If you'd rather split it
# (e.g. treat it as High since its midpoint $75k is right at the
# threshold), add "50-100" to whichever of the two lists above you prefer
# and remove it from this comment's exclusion.
INCOME_AMBIGUOUS_VALUES = ["50-100"]

# List 1090 is given directly (no name resolution needed/possible from a
# bare ID). The "imported" list is resolved by NAME via the Lists API,
# same never-hardcode-the-ID philosophy as everything else - see
# resolve_list_id_by_name_keywords.
APPT_SET_EXCLUDE_LIST_ID = "1090"
NEW_LEAD_NO_APPT_EXCLUDE_LIST_NAME_KEYWORDS = ["imported"]

APPT_SET_TOTAL_ROW_LABEL = "Total Appt Set"
APPT_SET_HIGH_INCOME_TOTAL_ROW_LABEL = "Total Appt Set High Income (75k+)"
APPT_SET_LOW_INCOME_TOTAL_ROW_LABEL = "Total Appt Set Low Income (0-75k)"

# CONFIRMED (round 4, see FIX F above) directly against the real HubSpot
# report (report 108263989): Classic List Membership is none of
# "imported" AND Date Created in period AND Appointment Set Calculation
# is NOT EQUAL TO 1. The earlier EQ "1" version was identical to the Appt
# Set filter (backwards for a "no appt" metric) and badly undercounted
# (233 vs. a real report total of 566 for the same period).
NEW_LEAD_NO_APPT_TOTAL_ROW_LABEL = "Total New Lead (no appt)"

APPT_SET_MEETINGS_COMPLETED_TOTAL_ROW_LABEL = "Total Appt Set Meetings Completed"
APPT_SET_SHOW_RATE_ROW_LABEL = "Appt Set: Show Rate"

# --- MM Recruits -------------------------------------------------------------
# FLAG: the filter you gave me ("Contact Owner on First Assigned Date is
# known" + Date Created in period) is the SAME base filter as the
# existing "Total Leads Assigned" block (filter_property HAS_PROPERTY +
# create-date range, no other conditions) - so this row will always equal
# the Leads Assigned Total row exactly. That may be intentional (the
# HubSpot report literally still shows "YTD Leads assigned" as its title
# in your screenshot, so "MM Recruits" may just be a renamed reuse of that
# same report) - flagging so you can confirm rather than silently
# duplicating a metric under two names.
MM_RECRUITS_TOTAL_ROW_LABEL = "Total MM Recruits [FLAG: same filter as Total Leads Assigned - verify]"
MM_RECRUITS_SAMANTHA_ROW_LABEL = "MM Recruits - Samantha"
SAMANTHA_OWNER_NAME_CONTAINS = "samantha"

# ---------------------------------------------------------------------------
# FIX (round 6) - deal-level SOURCE property resolution. See docstring
# points G and H above for the full failure this fixes.
#
# Your portal has NO deal property labeled exactly "Source*" (that label
# exists only on the CONTACT object, where it resolves fine to
# leconnex_source), and the old substring fallback (["source"]) matched 25
# different deal properties - Deal Source, Latest Traffic Source, Original
# Traffic Source, Record creation source, Source Object ID, and 20 more -
# so the resolver correctly refused to guess and exited.
#
# The real deal-level source property is "Deal Source " (internal:
# deal_source), taken straight from the candidate list that error printed.
# It's given directly below rather than resolved, for exactly the same
# reason INCOME_PROPERTY_OVERRIDE is: auto-resolution genuinely cannot
# disambiguate 25 candidates. Set the override back to None to return to
# auto-resolution, which will then use the exact label / fallback keywords
# beside it (both narrowed so exactly one property matches).
#
# WATCH THE FIELD TYPE printed by verify_deal_property_exists() at run
# time: the Google/AI Sales filters use CONTAINS_TOKEN, which is meant for
# string properties. If deal_source turns out to be an enumeration
# (dropdown), tell me its option labels and I'll switch those branches to
# an IN match on specific options instead - exactly like the income bands.
DEAL_SOURCE_PROPERTY_OVERRIDE = "deal_source"
DEAL_SOURCE_PROPERTY_EXACT_LABEL = "Deal Source"
DEAL_SOURCE_FALLBACK_KEYWORDS = ["deal source"]

# CONFIRMED ABSENT (round 6, from your live run): "Inferred Landing Page"
# exists on CONTACTS (inferred_landing_page) but there is NO such property
# on the DEAL object - the run's own error output listed the deal
# properties whose label contains "inferred" and that list came back
# COMPLETELY EMPTY. So the lookup is skipped entirely below rather than
# attempted-and-warned: it saves a pointless Properties API call and keeps
# the log honest about the fact that this is a known, confirmed gap rather
# than a transient resolution failure.
#
# CONSEQUENCE - the AI Sales # block runs on ONE branch (deal source
# contains "AI") instead of two. A closed-won deal whose only AI signal
# was a chatgpt landing page on the originating CONTACT will NOT be
# counted, so 'Total AI Sales #' (and 'Total Google + AI Sales #') may
# under-count relative to the contact-level 'Total AI/ChatGPT Leads
# Assigned' block, which DOES check both conditions. If you want those
# deals captured, the landing page has to reach the deal record somehow -
# either a HubSpot workflow that copies the contact's Inferred Landing
# Page onto the deal at creation (then set the override below to that new
# property's internal name), or a contact-association lookup per deal,
# which is a genuinely different and much more expensive query shape than
# anything currently in this script - say the word and I'll build it.
#
# Set ..._LOOKUP_ENABLED back to True (and/or fill in the override) once
# such a deal property exists.
DEAL_INFERRED_LANDING_PAGE_LOOKUP_ENABLED = False
DEAL_INFERRED_LANDING_PAGE_PROPERTY_OVERRIDE = None
DEAL_INFERRED_LANDING_PAGE_FALLBACK_KEYWORDS = ["inferred landing page"]

# ---------------------------------------------------------------------------
# NEW (round 5): Google Sales / AI Sales / Total / Close Rate of Google
# Leads - config.
#
# ASSUMPTION (FLAG - please confirm, same never-silently-wrong philosophy
# as the rest of this script): Google Sales / AI Sales reuse the EXACT
# SAME closed-won-stage + Closed won date + amount/owner/timezone logic
# as the existing combined Sales #/$ block, with one extra deal-level
# filter layered on top:
#   - Google Sales:  deal's source property contains exactly "Google"
#   - AI Sales:      deal's source property contains exactly "AI"  OR
#                    deal's Inferred Landing Page contains exactly
#                    "chatgpt"  (same two conditions as the existing
#                    AI/ChatGPT Leads block, just applied to the deal
#                    record instead of the contact record)
# This assumes the source (and, for AI Sales, Inferred Landing Page)
# values are copied onto the DEAL record itself - e.g. via a workflow
# that syncs them from the associated contact when the deal is created.
# Shown as a COUNT (Sales #), matching the New Business # style, not a
# dollar amount - flag if you want $ too.
GOOGLE_SALES_TOTAL_ROW_LABEL = "Total Google Sales #"
AI_SALES_TOTAL_ROW_LABEL = "Total AI Sales #"
GOOGLE_AI_SALES_TOTAL_ROW_LABEL = "Total Google + AI Sales #"

# ASSUMPTION (FLAG - please confirm): "Close rate of google leads" is
# computed as Google Sales # / Total Google Leads Assigned - using the
# ALREADY-EXISTING "Total Google Leads Assigned" block above (Source*
# contains exactly "Google", confirmed against your saved-view
# screenshot in an earlier round; that block is NOT modified here),
# shown as a percentage, same convention as the existing Appt Set: Show
# Rate row. You described the ratio the other way round (Leads / Sales);
# that would read as a number well over 100% in the normal case (many
# more leads than sales), which isn't how a close rate is usually read,
# so this flips it to Sales / Leads - say the word if you actually want
# it the other way.
GOOGLE_CLOSE_RATE_ROW_LABEL = "Close Rate of Google Leads"

# ---------------------------------------------------------------------------
# NEW: Daily tab (Calls / Meetings / Sales / Hours by owner, one column per
# calendar day) - config.
#
# Confirmed against the real HubSpot reports you shared:
#   - Calls:    Activity type is any of Call (satisfied automatically by
#               querying the /crm/v3/objects/calls/search endpoint, exactly
#               like the existing Calls block above - that endpoint only
#               ever returns call engagements) + Activity date in the day
#               (UTC, matching CALLS_TIMEZONE above).
#   - Meetings: Meeting outcome is any of Completed + Activity date in the
#               day (EDT, matching MEETINGS_TIMEZONE above) - identical
#               filter to the existing Meetings Completed block.
#   - Sales:    Deal stage is any of "Closed won" or "Renewal - Closed won"
#               (Sales Pipeline) + Closed won date in the day (UTC, matching
#               SALES_TIMEZONE above) - identical filter to the existing
#               combined Sales #/$ block; the Daily tab shows the deal
#               COUNT only (Sales #), not the dollar amount.
#   - Hours:    left BLANK per your instruction - no HubSpot property for
#               hours worked was given, so this block is written with
#               owner rows but empty cells, rather than guessed at.
# All three real blocks reuse the exact same already-resolved properties/
# filters as the existing Meetings/Calls/Sales blocks above - nothing new
# to resolve, and none of those existing blocks are touched.
# ---------------------------------------------------------------------------
DAILY_SHEET_TAB_NAME = "Daily"
DAILY_CALLS_TOTAL_ROW_LABEL = "Total Calls"
DAILY_MEETINGS_TOTAL_ROW_LABEL = "Total Meetings Completed"
DAILY_SALES_TOTAL_ROW_LABEL = "Total Sales #"
DAILY_HOURS_TOTAL_ROW_LABEL = "Total Hours"

# ---------------------------------------------------------------------------
# NEW (round 7): FREEZE COMPLETED PERIODS.
#
# Previously EVERY cell was re-fetched live on every run - all 30 blocks x
# every week/month/year column, back to April 2024. That is thousands of
# HubSpot queries to recompute columns whose underlying records finished
# changing months ago.
#
# With freezing on, a period is re-fetched only if it is still moving:
#   - period.live is True (the current month total, the current year YTD,
#     and the running current-week quick-glance column), OR
#   - the period ENDS on/after the refresh cutoff - by default the 1st of
#     the current month, so every week inside the current month refreshes
#     too, as does the Previous Week column whenever it falls in this month.
# Everything older is read straight out of the previous run's sheet.
#
# HOW THE OLD VALUES SURVIVE: write_to_sheet() deletes and recreates the
# worksheet each run, so the previous values have to be READ BEFORE that
# happens - see read_frozen_sheet(), called at the very top of main().
# Values are matched by (block Total-row label, column label, owner name),
# so inserting a new week column or a new owner row never shifts a frozen
# value into the wrong cell.
#
# THE TRADE-OFF, STATED PLAINLY: a frozen month will NOT pick up records
# that get backdated into it, or records whose owner/stage/amount is edited
# after the fact. HubSpot data does get edited retroactively - your own
# workbook showed exactly that (income bands changed under an already-built
# pivot). Two dials for this:
#   - REFRESH_TRAILING_DAYS pushes the cutoff further back, so the last N
#     days of history are always re-fetched (e.g. 45 re-does roughly the
#     last month and a half every run).
#   - FREEZE_COMPLETED_PERIODS = False restores the old behaviour - every
#     cell live, every run - for a periodic full rebuild.
FREEZE_COMPLETED_PERIODS = True
REFRESH_TRAILING_DAYS = 0

# Daily-tab columns (single-day periods) use their own, shorter window:
# only today and the previous DAILY_REFRESH_TRAILING_DAYS day(s) are
# re-fetched; older days are reused from the sheet. 1 = today + yesterday.
DAILY_REFRESH_TRAILING_DAYS = 1

# Every block whose values are FETCHED (and therefore freezable), keyed by
# the Total-row label that identifies it in the sheet. Derived blocks (the
# ratio and sum rows - Avg Sale $, Sales/Leads, Organic Leads, Show Rate,
# Close Rate, Google + AI Sales) are deliberately absent: they are pure
# arithmetic over these blocks, so they recompute correctly from whatever
# mix of frozen and freshly-fetched numbers they're handed.
MASTER_FREEZABLE_BLOCK_LABELS = None   # populated at import time, below
DAILY_FREEZABLE_BLOCK_LABELS = None

# Service-account key is NOT stored in this file. Set GOOGLE_SERVICE_ACCOUNT_JSON
# (GitHub Actions secret, or a local environment variable) to the full JSON key.
_LOCAL_SERVICE_ACCOUNT_INFO_FALLBACK = None


def _load_service_account_info():
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            sys.exit(f"ERROR: GOOGLE_SERVICE_ACCOUNT_JSON is set but isn't valid JSON: {e}")
    if _LOCAL_SERVICE_ACCOUNT_INFO_FALLBACK is None:
        sys.exit("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set - "
                 "set it to the full service account JSON key.")
    return _LOCAL_SERVICE_ACCOUNT_INFO_FALLBACK


SERVICE_ACCOUNT_INFO = _load_service_account_info()


def get_access_token():
    token = os.environ.get("HUBSPOT_ACCESS_TOKEN")
    if not token:
        sys.exit(
            "ERROR: HUBSPOT_ACCESS_TOKEN environment variable not set.\n"
            "Set it with: export HUBSPOT_ACCESS_TOKEN='pat-na1-xxxxxxxx'"
        )
    return token


# ---------------------------------------------------------------------------
# Small retry helper (used by the Meetings/Calls/Deals/Owners fetch
# functions below; the original Leads functions are untouched)
# ---------------------------------------------------------------------------

def request_with_retry(method, url, max_retries=5, **kwargs):
    """Same as requests.request(), but retries on:
      - 429 (honoring Retry-After)
      - transient 5xx server errors (exponential backoff) - HubSpot
        occasionally returns a bare 500 on an otherwise-normal query that
        succeeds on retry, so treating any 5xx as fatal kills a run over
        something that usually clears itself within a couple seconds.
      - connection-level failures (DNS hiccup, dropped Wi-Fi/VPN,
        connection reset, read timeout). These raise a
        requests.exceptions.ConnectionError/Timeout BEFORE a response
        object even exists, so they used to propagate straight out and
        kill the whole run over a one-second network blip. A 30s timeout
        is also set (kwargs can still override it) so a hung connection
        doesn't block forever instead of hitting this retry path."""
    kwargs.setdefault("timeout", 30)
    last_network_exc = None
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            last_network_exc = exc
            wait = 2 ** attempt
            print(f"  Network error ({exc.__class__.__name__}) - waiting {wait}s before retry ({attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue
        if resp.status_code == 429:
            wait = float(resp.headers.get("Retry-After", 2 ** attempt))
            print(f"  Rate limited (429) - waiting {wait}s before retry ({attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue
        if resp.status_code >= 500:
            wait = 2 ** attempt
            print(f"  HubSpot server error ({resp.status_code}) - waiting {wait}s before retry ({attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue
        if 400 <= resp.status_code < 500:
            # NEW - HubSpot's 4xx error bodies almost always contain a
            # 'message' field explaining EXACTLY what's wrong with the
            # request (e.g. too many filters in a filterGroup, an invalid
            # operator for a property's type, an unindexed property used
            # in a filter). resp.raise_for_status() alone throws that body
            # away, leaving just a bare "400 Client Error: Bad Request"
            # with no way to diagnose it - print the body here (once, not
            # retried, since a 4xx is a request problem that won't fix
            # itself on retry) so the real cause is visible in the log.
            try:
                error_body = resp.json()
            except ValueError:
                error_body = resp.text
            print(f"  HubSpot rejected the request ({resp.status_code}) for {url}\n  Request body: {kwargs.get('json')}\n  Response body: {error_body}")
        resp.raise_for_status()
        return resp
    if last_network_exc is not None:
        raise last_network_exc
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Property resolution (Leads path UNCHANGED; object_type/exit_on_failure are
# optional params so the existing call sites keep working as-is)
# ---------------------------------------------------------------------------

def resolve_property(token, label_keywords, purpose, object_type="contacts", exit_on_failure=True):
    """Finds the internal property name whose LABEL contains every keyword
    in label_keywords (case-insensitive), on the given object_type. Exits
    with a clear error if more than one property matches (always - ambiguity
    is never acceptable). If zero match and exit_on_failure is False,
    returns None instead of exiting, so callers can try a fallback keyword
    set (see resolve_owner_property_for_object)."""
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = f"https://api.hubapi.com/crm/v3/properties/{object_type}"
    resp = request_with_retry("GET", endpoint, headers=headers)
    props = resp.json().get("results", [])
    keywords_lower = [k.lower() for k in label_keywords]
    matches = [
        p for p in props
        if all(kw in (p.get("label") or "").lower() for kw in keywords_lower)
    ]

    if not matches:
        if not exit_on_failure:
            return None
        filter_term = "owner" if any("owner" in kw for kw in keywords_lower) else keywords_lower[0].split()[0]
        available = "\n".join(f"  - {p.get('label')}  (internal: {p.get('name')})" for p in props if filter_term in (p.get("label") or "").lower())
        sys.exit(
            f"ERROR: no {object_type} property label matched {label_keywords} (looking for the {purpose} property).\n"
            f"Candidate properties containing '{filter_term}':\n{available}\n"
            f"Update the relevant *_LABEL_KEYWORDS constant to match the exact label shown in "
            f"HubSpot > Settings > Properties > {object_type}."
        )
    if len(matches) > 1:
        names = "\n".join(f"  - {p.get('label')}  (internal: {p.get('name')})" for p in matches)
        sys.exit(
            f"ERROR: multiple {object_type} properties matched {label_keywords} (looking for the {purpose} property):\n{names}\n"
            f"Narrow the relevant *_LABEL_KEYWORDS constant so exactly one matches."
        )

    prop = matches[0]
    print(f"Resolved {purpose} property on {object_type}: '{prop.get('label')}' -> internal name '{prop.get('name')}'")
    return prop["name"]


def resolve_owner_property_for_object(token, object_type):
    """Tries the 'activity assigned to' label first; falls back to a bare
    'owner' label match if that's not found (some portals label engagement
    owner fields differently). Errors out clearly if neither matches."""
    result = resolve_property(token, ACTIVITY_OWNER_LABEL_KEYWORDS, "activity owner", object_type=object_type, exit_on_failure=False)
    if result:
        return result
    print(f"No {object_type} property labeled like {ACTIVITY_OWNER_LABEL_KEYWORDS} - falling back to {ACTIVITY_OWNER_LABEL_FALLBACK_KEYWORDS}.")
    return resolve_property(token, ACTIVITY_OWNER_LABEL_FALLBACK_KEYWORDS, "activity owner", object_type=object_type, exit_on_failure=True)


def resolve_activity_date_property(token, object_type):
    return resolve_property(token, ACTIVITY_DATE_LABEL_KEYWORDS, "activity date", object_type=object_type)


def resolve_meeting_outcome_completed_value(token):
    """Resolves the meeting outcome property by label, then resolves its
    'Completed' OPTION by label too (rather than assuming the internal
    enum value is literally 'COMPLETED') - same never-hardcode philosophy
    as the rest of this script."""
    outcome_property = resolve_property(token, MEETING_OUTCOME_LABEL_KEYWORDS, "meeting outcome", object_type="meetings")
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", f"https://api.hubapi.com/crm/v3/properties/meetings/{outcome_property}", headers=headers)
    options = resp.json().get("options", [])
    for opt in options:
        if MEETING_OUTCOME_TARGET_LABEL in (opt.get("label") or "").lower():
            print(f"Resolved meeting outcome '{MEETING_OUTCOME_TARGET_LABEL}' -> internal value '{opt.get('value')}'")
            return outcome_property, opt["value"]
    available = "\n".join(f"  - {o.get('label')} (value: {o.get('value')})" for o in options)
    sys.exit(
        f"ERROR: no option labeled like '{MEETING_OUTCOME_TARGET_LABEL}' found on meeting outcome property "
        f"'{outcome_property}'.\nAvailable options:\n{available}"
    )


def resolve_deal_owner_property(token):
    """'Deal owner' is a substring of BOTH the plain user-facing property
    ('Deal owner') AND unrelated properties like 'Average Deal Owner
    Duration In Current Stage' - so, same issue as
    resolve_closed_won_date_property below, a plain substring match on
    DEAL_OWNER_LABEL_KEYWORDS is ambiguous.

    FIX: resolve via an EXACT (not substring) case-insensitive label match
    first, so 'Deal owner' matches but 'Average Deal Owner Duration In
    Current Stage' does not. Falls back to the old substring-based
    resolve_property() (then to a bare 'owner' label match) only if no
    exact match is found, so a portal with a differently-worded owner
    property still resolves."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", "https://api.hubapi.com/crm/v3/properties/deals", headers=headers)
    props = resp.json().get("results", [])
    exact_matches = [p for p in props if (p.get("label") or "").strip().lower() == "deal owner"]
    if len(exact_matches) == 1:
        prop = exact_matches[0]
        print(f"Resolved deal owner property (exact label match): '{prop.get('label')}' -> '{prop.get('name')}'")
        return prop["name"]
    if len(exact_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (internal: {p.get('name')})" for p in exact_matches)
        sys.exit(f"ERROR: multiple deal properties are labeled exactly 'Deal owner':\n{names}\nPick one and hardcode it.")
    print("No deal property labeled exactly 'Deal owner' found - falling back to substring match.")
    result = resolve_property(token, DEAL_OWNER_LABEL_KEYWORDS, "deal owner", object_type="deals", exit_on_failure=False)
    if result:
        return result
    print(f"No deals property labeled like {DEAL_OWNER_LABEL_KEYWORDS} - falling back to a bare 'owner' label match.")
    return resolve_property(token, ACTIVITY_OWNER_LABEL_FALLBACK_KEYWORDS, "deal owner", object_type="deals", exit_on_failure=True)


def resolve_closed_won_date_property(token):
    """'Closed won date' is a substring of BOTH the plain user-facing
    property ('Closed won date') AND an '(Internal)' variant some portals
    also have ('Closed Won Date (Internal)') - so unlike most
    *_LABEL_KEYWORDS resolvers in this script, a plain substring match on
    CLOSED_WON_DATE_LABEL_KEYWORDS is ambiguous and resolve_property()
    correctly refuses to guess.

    FIX: resolve via an EXACT (not substring) case-insensitive label match
    first, so 'Closed won date' matches but 'Closed Won Date (Internal)'
    does not - same pattern already used by resolve_amount_property() for
    the analogous 'Amount' vs 'Amount in company currency' ambiguity.
    Falls back to the old substring-based resolve_property() only if no
    exact match is found, so a portal that genuinely has just one
    "closed won date"-ish property (worded differently) still resolves."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", "https://api.hubapi.com/crm/v3/properties/deals", headers=headers)
    props = resp.json().get("results", [])
    exact_matches = [p for p in props if (p.get("label") or "").strip().lower() == "closed won date"]
    if len(exact_matches) == 1:
        prop = exact_matches[0]
        print(f"Resolved closed won date property (exact label match): '{prop.get('label')}' -> '{prop.get('name')}'")
        return prop["name"]
    if len(exact_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (internal: {p.get('name')})" for p in exact_matches)
        sys.exit(
            f"ERROR: multiple deal properties are labeled exactly 'Closed won date':\n{names}\n"
            f"Pick one and hardcode it as a CLOSED_WON_DATE_PROPERTY_OVERRIDE."
        )
    print("No deal property labeled exactly 'Closed won date' found - falling back to substring match.")
    return resolve_property(token, CLOSED_WON_DATE_LABEL_KEYWORDS, "closed won date", object_type="deals")


def resolve_amount_property(token):
    """'Amount' is too short/generic a word for the usual substring
    resolver - it would also match things like 'Amount in company
    currency' or a custom 'Renewal Amount' property, risking a false
    'multiple matches' error on a portal that has any of those. Deal
    amount needs an EXACT (not substring) label match instead. Falls back
    to HubSpot's fixed internal 'amount' property (present on every
    portal, can be relabeled but never deleted/renamed internally) if no
    property is labeled exactly 'Amount'."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", "https://api.hubapi.com/crm/v3/properties/deals", headers=headers)
    props = resp.json().get("results", [])
    exact_matches = [p for p in props if (p.get("label") or "").strip().lower() == "amount"]
    if len(exact_matches) == 1:
        prop = exact_matches[0]
        print(f"Resolved deal amount property (exact label match): '{prop.get('label')}' -> '{prop.get('name')}'")
        return prop["name"]
    if len(exact_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (internal: {p.get('name')})" for p in exact_matches)
        sys.exit(f"ERROR: multiple deal properties are labeled exactly 'Amount':\n{names}\nPick one and hardcode it as DEAL_AMOUNT_PROPERTY_OVERRIDE.")
    print("No deal property labeled exactly 'Amount' found - falling back to HubSpot's standard internal 'amount' property.")
    return "amount"


def resolve_closed_won_dealstages(token):
    """Resolves via the Pipelines API (crm/v3/pipelines/deals), NOT the
    generic Properties API - dealstage values are unique per (pipeline,
    stage) pair, so this is the only reliable way to scope "Closed won" +
    "Renewal - Closed won" to specifically the "Sales Pipeline" pipeline
    (both were shown suffixed "(Sales Pipeline)" in the report screenshot)
    rather than picking up a same-named stage in some other pipeline.
    Returns a list of stage IDs - naturally covers both required stages
    from one substring match on "closed won" (which "Renewal - Closed won"
    also contains), without hardcoding a count of 2 or specific IDs.
    UNCHANGED - still returns BOTH stages together; the two new
    single-stage resolvers below are separate functions so this one and
    the existing combined Sales #/$ block that depends on it are untouched."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", "https://api.hubapi.com/crm/v3/pipelines/deals", headers=headers)
    pipelines = resp.json().get("results", [])
    pipeline_keywords = [k.lower() for k in DEAL_PIPELINE_LABEL_KEYWORDS]
    pipeline_matches = [p for p in pipelines if all(kw in (p.get("label") or "").lower() for kw in pipeline_keywords)]
    if not pipeline_matches:
        available = "\n".join(f"  - {p.get('label')} (id: {p.get('id')})" for p in pipelines)
        sys.exit(f"ERROR: no deal pipeline label matched {DEAL_PIPELINE_LABEL_KEYWORDS}.\nAvailable pipelines:\n{available}")
    if len(pipeline_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (id: {p.get('id')})" for p in pipeline_matches)
        sys.exit(f"ERROR: multiple deal pipelines matched {DEAL_PIPELINE_LABEL_KEYWORDS}:\n{names}\nNarrow DEAL_PIPELINE_LABEL_KEYWORDS.")
    pipeline = pipeline_matches[0]
    print(f"Resolved deal pipeline: '{pipeline.get('label')}' -> id '{pipeline.get('id')}'")

    stage_keywords = [k.lower() for k in CLOSED_WON_STAGE_LABEL_KEYWORDS]
    stage_matches = [s for s in pipeline.get("stages", []) if all(kw in (s.get("label") or "").lower() for kw in stage_keywords)]
    if not stage_matches:
        available = "\n".join(f"  - {s.get('label')} (id: {s.get('id')})" for s in pipeline.get("stages", []))
        sys.exit(f"ERROR: no stage in pipeline '{pipeline.get('label')}' matched {CLOSED_WON_STAGE_LABEL_KEYWORDS}.\nAvailable stages:\n{available}")
    for s in stage_matches:
        print(f"Resolved closed-won stage: '{s.get('label')}' -> id '{s.get('id')}'")
    return [s["id"] for s in stage_matches]


def resolve_deal_stage_by_exact_label(token, target_label):
    """NEW - resolves a SINGLE dealstage ID by an EXACT (not substring)
    case-insensitive label match within the Sales Pipeline. Deliberately
    duplicates the pipeline-lookup portion of resolve_closed_won_dealstages()
    above rather than refactoring that function, so the existing combined
    Sales #/$ block's code path is left completely untouched. Used to
    scope New Business to ONLY "Closed won" and Renewals to ONLY
    "Renewal - Closed won", so the two never overlap."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", "https://api.hubapi.com/crm/v3/pipelines/deals", headers=headers)
    pipelines = resp.json().get("results", [])
    pipeline_keywords = [k.lower() for k in DEAL_PIPELINE_LABEL_KEYWORDS]
    pipeline_matches = [p for p in pipelines if all(kw in (p.get("label") or "").lower() for kw in pipeline_keywords)]
    if not pipeline_matches:
        available = "\n".join(f"  - {p.get('label')} (id: {p.get('id')})" for p in pipelines)
        sys.exit(f"ERROR: no deal pipeline label matched {DEAL_PIPELINE_LABEL_KEYWORDS}.\nAvailable pipelines:\n{available}")
    if len(pipeline_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (id: {p.get('id')})" for p in pipeline_matches)
        sys.exit(f"ERROR: multiple deal pipelines matched {DEAL_PIPELINE_LABEL_KEYWORDS}:\n{names}\nNarrow DEAL_PIPELINE_LABEL_KEYWORDS.")
    pipeline = pipeline_matches[0]

    stage_matches = [
        s for s in pipeline.get("stages", [])
        if (s.get("label") or "").strip().lower() == target_label.strip().lower()
    ]
    if not stage_matches:
        available = "\n".join(f"  - {s.get('label')} (id: {s.get('id')})" for s in pipeline.get("stages", []))
        sys.exit(
            f"ERROR: no stage in pipeline '{pipeline.get('label')}' labeled exactly '{target_label}'.\n"
            f"Available stages:\n{available}"
        )
    if len(stage_matches) > 1:
        names = "\n".join(f"  - {s.get('label')} (id: {s.get('id')})" for s in stage_matches)
        sys.exit(f"ERROR: multiple stages in pipeline '{pipeline.get('label')}' are labeled exactly '{target_label}':\n{names}")
    stage = stage_matches[0]
    print(f"Resolved dealstage '{target_label}' -> id '{stage.get('id')}'")
    return stage["id"]


def resolve_old_lead_yes_value(token):
    """NEW - resolves the 'Yes' option on the Old Lead (60+ Days)? deal
    dropdown (OLD_LEAD_PROPERTY) by label match, same never-hardcode-the-
    enum-value philosophy as resolve_meeting_outcome_completed_value()
    above. Errors out with the full option list if OLD_LEAD_YES_LABEL_KEYWORDS
    doesn't match anything, so a mismatch is loud and immediately fixable
    rather than silently returning 0 for this whole block."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", f"https://api.hubapi.com/crm/v3/properties/deals/{OLD_LEAD_PROPERTY}", headers=headers)
    options = resp.json().get("options", [])
    keywords_lower = [k.lower() for k in OLD_LEAD_YES_LABEL_KEYWORDS]
    matches = [o for o in options if all(kw in (o.get("label") or "").lower() for kw in keywords_lower)]
    if not matches:
        available = "\n".join(f"  - {o.get('label')} (value: {o.get('value')})" for o in options)
        sys.exit(
            f"ERROR: no option on deal property '{OLD_LEAD_PROPERTY}' labeled like {OLD_LEAD_YES_LABEL_KEYWORDS}.\n"
            f"Available options:\n{available}\nUpdate OLD_LEAD_YES_LABEL_KEYWORDS to match the exact label."
        )
    if len(matches) > 1:
        names = "\n".join(f"  - {o.get('label')} (value: {o.get('value')})" for o in matches)
        sys.exit(f"ERROR: multiple options on '{OLD_LEAD_PROPERTY}' matched {OLD_LEAD_YES_LABEL_KEYWORDS}:\n{names}\nNarrow OLD_LEAD_YES_LABEL_KEYWORDS.")
    opt = matches[0]
    print(f"Resolved old-lead 'yes' value: '{opt.get('label')}' -> '{opt.get('value')}'")
    return opt["value"]


def resolve_contact_property_exact_label(token, target_label, purpose, fallback_keywords=None):
    """NEW - generic exact-label resolver for contact properties, same
    pattern as resolve_amount_property/resolve_closed_won_date_property/
    resolve_deal_owner_property above (all of which resolve DEAL
    properties by exact label) - this is the contacts-object counterpart,
    used for Source*, Appointment Set Calculation, Date Met With
    (face-to-face), Income, and Inferred Landing Page. Falls back to the
    substring resolve_property() (using fallback_keywords, or the
    lowercased label itself if none given) only if no exact match is
    found."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", PROPERTIES_ENDPOINT, headers=headers)
    props = resp.json().get("results", [])
    exact_matches = [p for p in props if (p.get("label") or "").strip().lower() == target_label.strip().lower()]
    if len(exact_matches) == 1:
        prop = exact_matches[0]
        print(f"Resolved {purpose} property (exact label match): '{prop.get('label')}' -> '{prop.get('name')}'")
        return prop["name"]
    if len(exact_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (internal: {p.get('name')})" for p in exact_matches)
        sys.exit(f"ERROR: multiple contact properties are labeled exactly '{target_label}' (looking for {purpose}):\n{names}\nPick one and hardcode it.")
    print(f"No contact property labeled exactly '{target_label}' found - falling back to substring match.")
    keywords = fallback_keywords or [target_label.lower().rstrip("*").strip()]
    return resolve_property(token, keywords, purpose, object_type="contacts")


def resolve_deal_property_exact_label(token, target_label, purpose, fallback_keywords=None):
    """NEW (round 5) - generic exact-label resolver for DEAL properties,
    the deals-object counterpart of resolve_contact_property_exact_label
    above (same pattern: exact match first, substring fallback). Used to
    resolve a deal-level source (and, for AI Sales, 'Inferred Landing
    Page') property for the new Google Sales / AI Sales blocks."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", "https://api.hubapi.com/crm/v3/properties/deals", headers=headers)
    props = resp.json().get("results", [])
    exact_matches = [p for p in props if (p.get("label") or "").strip().lower() == target_label.strip().lower()]
    if len(exact_matches) == 1:
        prop = exact_matches[0]
        print(f"Resolved {purpose} deal property (exact label match): '{prop.get('label')}' -> '{prop.get('name')}'")
        return prop["name"]
    if len(exact_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (internal: {p.get('name')})" for p in exact_matches)
        sys.exit(f"ERROR: multiple deal properties are labeled exactly '{target_label}' (looking for {purpose}):\n{names}\nPick one and hardcode it.")
    print(f"No deal property labeled exactly '{target_label}' found - falling back to substring match.")
    keywords = fallback_keywords or [target_label.lower().rstrip("*").strip()]
    return resolve_property(token, keywords, purpose, object_type="deals")


def verify_deal_property_exists(token, property_name, purpose):
    """NEW (round 6) - when a *_PROPERTY_OVERRIDE is set, label-based
    resolution is skipped entirely, so nothing would otherwise catch a
    typo'd or deleted internal name until every query built on it
    silently returned 0. This fetches the property directly and prints
    its real label and field type, so a bad override fails immediately
    with a 404 (loudly, via request_with_retry) instead of quietly
    poisoning a whole block. Same spirit as verify_income_property_type.

    WATCH THE PRINTED TYPE: the Google/AI Sales filters use
    CONTAINS_TOKEN, which is meant for string properties. If this prints
    type='enumeration' (a dropdown), tell me its option labels and those
    two branches should switch to an IN match on the specific options
    instead - exactly like the income bands."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", f"https://api.hubapi.com/crm/v3/properties/deals/{property_name}", headers=headers)
    prop = resp.json()
    print(
        f"Using manual {purpose} deal property override: '{property_name}' "
        f"(label: '{prop.get('label')}', type: {prop.get('type')}/{prop.get('fieldType')}) - auto-resolution skipped."
    )
    return property_name


def resolve_deal_property_optional(token, target_label, purpose, fallback_keywords=None):
    """NEW (round 6) - identical exact-label-then-substring resolution to
    resolve_deal_property_exact_label above, except it RETURNS None
    instead of sys.exit()ing when the property doesn't exist or when the
    substring fallback is ambiguous. Used only for the optional
    deal-level 'Inferred Landing Page' property - see the config note on
    DEAL_INFERRED_LANDING_PAGE_PROPERTY_OVERRIDE for why that one branch
    is allowed to be missing while the source property is not."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", "https://api.hubapi.com/crm/v3/properties/deals", headers=headers)
    props = resp.json().get("results", [])

    exact_matches = [p for p in props if (p.get("label") or "").strip().lower() == target_label.strip().lower()]
    if len(exact_matches) == 1:
        prop = exact_matches[0]
        print(f"Resolved {purpose} deal property (exact label match): '{prop.get('label')}' -> '{prop.get('name')}'")
        return prop["name"]
    if len(exact_matches) > 1:
        names = "\n".join(f"  - {p.get('label')} (internal: {p.get('name')})" for p in exact_matches)
        print(
            f"WARNING: multiple deal properties are labeled exactly '{target_label}' (looking for {purpose}):\n{names}\n"
            f"Skipping this branch - set the matching *_OVERRIDE constant to pick one."
        )
        return None

    keywords = [k.lower() for k in (fallback_keywords or [target_label.lower().rstrip("*").strip()])]
    matches = [p for p in props if all(kw in (p.get("label") or "").lower() for kw in keywords)]
    if len(matches) == 1:
        prop = matches[0]
        print(f"Resolved {purpose} deal property (substring match on {keywords}): '{prop.get('label')}' -> '{prop.get('name')}'")
        return prop["name"]
    if not matches:
        print(f"WARNING: no deal property labeled exactly '{target_label}', and none matching {keywords} (looking for {purpose}) - skipping this branch.")
    else:
        names = "\n".join(f"  - {p.get('label')} (internal: {p.get('name')})" for p in matches)
        print(
            f"WARNING: {len(matches)} deal properties matched {keywords} (looking for {purpose}) - too ambiguous to pick:\n{names}\n"
            f"Skipping this branch - set the matching *_OVERRIDE constant to pick one."
        )
    return None


def resolve_contact_property_option_values(token, property_name, option_label_keywords_list, purpose):
    """NEW - resolves one or more OPTION values on a contact property by
    label, same never-hardcode-the-enum-value philosophy as
    resolve_meeting_outcome_completed_value/resolve_old_lead_yes_value
    above. option_label_keywords_list is a list of keyword-lists (one per
    option you need resolved) - e.g. [["duplicate"], ["don't work"]] for
    two options to exclude. Returns a list of resolved internal option
    values, in the same order.

    FIX (D): the returned list is now DE-DUPLICATED (order-preserving),
    for portals where two keyword groups happen to resolve to the same
    combined option (e.g. a single "Duplicate, Don't Work" option)."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", f"{PROPERTIES_ENDPOINT}/{property_name}", headers=headers)
    options = resp.json().get("options", [])
    resolved = []
    for kw_group in option_label_keywords_list:
        kws = [k.lower() for k in kw_group]
        matches = [o for o in options if all(kw in (o.get("label") or "").lower() for kw in kws)]
        if not matches:
            available = "\n".join(f"  - {o.get('label')} (value: {o.get('value')})" for o in options)
            sys.exit(f"ERROR: no option on contact property '{property_name}' labeled like {kw_group} (looking for {purpose}).\nAvailable options:\n{available}")
        if len(matches) > 1:
            names = "\n".join(f"  - {o.get('label')} (value: {o.get('value')})" for o in matches)
            sys.exit(f"ERROR: multiple options on '{property_name}' matched {kw_group} (looking for {purpose}):\n{names}")
        opt = matches[0]
        print(f"Resolved {purpose} option: '{opt.get('label')}' -> '{opt.get('value')}'")
        resolved.append(opt["value"])

    seen = set()
    deduped = []
    for v in resolved:
        if v in seen:
            continue
        seen.add(v)
        deduped.append(v)
    if len(deduped) != len(resolved):
        print(f"  (de-duplicated {len(resolved)} resolved {purpose} option value(s) down to {len(deduped)} distinct value(s))")
    return deduped


LISTS_SEARCH_ENDPOINT = "https://api.hubapi.com/crm/v3/lists/search"


def verify_income_property_type(token, income_property, expected_values):
    """NEW - the Appt Set High/Low Income filters match specific dropdown
    option VALUES (INCOME_LOW_VALUES / INCOME_HIGH_VALUES, confirmed live
    against your portal - see those constants' comments), via IN. This
    only produces correct results if income_property is still the same
    enumeration/dropdown with those same option values. Rather than
    silently returning wrong (likely zero, or under-counted) totals if the
    property ever changes shape (a label edit, a removed option, or - if
    you've swapped INCOME_PROPERTY_OVERRIDE to a different property - a
    completely different set of options), this checks the property's real
    current option values via the Properties API before either income
    block runs any query, and exits loudly if any of the expected_values
    (the union of INCOME_LOW_VALUES + INCOME_HIGH_VALUES) are missing from
    what the property actually has right now."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = request_with_retry("GET", f"{PROPERTIES_ENDPOINT}/{income_property}", headers=headers)
    prop = resp.json()
    prop_type = prop.get("type")
    field_type = prop.get("fieldType")
    options = prop.get("options", [])
    actual_values = {o.get("value") for o in options}
    missing = [v for v in expected_values if v not in actual_values]
    available = "\n".join(f"  - {o.get('label')}  (value: {o.get('value')})" for o in options) or "  (no options returned)"
    if missing:
        sys.exit(
            f"ERROR: income property '{income_property}' (type='{prop_type}'/'{field_type}') no longer has these "
            f"expected option value(s), which INCOME_LOW_VALUES/INCOME_HIGH_VALUES rely on: {missing}.\n"
            f"Current option labels/values on '{income_property}':\n{available}\n"
            f"Update INCOME_LOW_VALUES/INCOME_HIGH_VALUES/INCOME_AMBIGUOUS_VALUES to match."
        )
    print(f"Confirmed income property '{income_property}' still has all {len(expected_values)} expected band values - IN-based income filters are valid.")


def resolve_list_id_by_name_keywords(token, keywords, purpose):
    """NEW - resolves a classic/active HubSpot list's ID by NAME (via the
    v3 Lists API's search endpoint), same never-hardcode-the-ID philosophy
    as every other resolver in this script - used for the "imported" list
    exclusion (New Lead (no appt), Appt Set Meetings Completed). The
    "Appt Set" block's list (1090) is given directly as an ID in your
    instructions, so it skips this resolver and goes straight to
    fetch_list_membership_ids().

    Tries an EXACT (not substring) case-insensitive name match FIRST -
    same exact-match-before-substring pattern used throughout this script
    (resolve_amount_property, resolve_deal_owner_property,
    resolve_closed_won_date_property, resolve_contact_property_exact_label)
    - since a bare keyword like "imported" is a substring of unrelated
    list names too (e.g. "Imported Contacts", "...Not Imported..."), and
    only falls back to substring matching if no single exact match is
    found."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"query": keywords[0], "count": 100}
    resp = request_with_retry("POST", LISTS_SEARCH_ENDPOINT, headers=headers, json=body)
    lists_ = resp.json().get("lists", [])

    target_name = " ".join(keywords).strip().lower()
    exact_matches = [l for l in lists_ if (l.get("name") or "").strip().lower() == target_name]
    if len(exact_matches) == 1:
        lst = exact_matches[0]
        list_id = str(lst.get("listId") if lst.get("listId") is not None else lst.get("listVersion", {}).get("listId") or lst.get("id"))
        print(f"Resolved list ({purpose}) via exact name match: '{lst.get('name')}' -> id '{list_id}'")
        return list_id
    if len(exact_matches) > 1:
        names = "\n".join(f"  - {l.get('name')} (id: {l.get('listId')})" for l in exact_matches)
        sys.exit(f"ERROR: multiple HubSpot lists are named exactly '{target_name}' (looking for the {purpose} list):\n{names}\nPick one and hardcode its ID.")

    print(f"No HubSpot list named exactly '{target_name}' found - falling back to substring match.")
    keywords_lower = [k.lower() for k in keywords]
    matches = [l for l in lists_ if all(kw in (l.get("name") or "").lower() for kw in keywords_lower)]
    if not matches:
        available = "\n".join(f"  - {l.get('name')} (id: {l.get('listId')})" for l in lists_)
        sys.exit(f"ERROR: no HubSpot list name matched {keywords} (looking for the {purpose} list).\nCandidates returned by the Lists search API:\n{available}")
    if len(matches) > 1:
        names = "\n".join(f"  - {l.get('name')} (id: {l.get('listId')})" for l in matches)
        sys.exit(f"ERROR: multiple HubSpot lists matched {keywords} (looking for the {purpose} list):\n{names}\nNarrow the keywords.")
    lst = matches[0]
    list_id = str(lst.get("listId") if lst.get("listId") is not None else lst.get("listVersion", {}).get("listId") or lst.get("id"))
    print(f"Resolved list ({purpose}) via substring match: '{lst.get('name')}' -> id '{list_id}'")
    return list_id


def fetch_list_membership_ids(token, list_id):
    """NEW - fetches every contact ID currently in the given list, via the
    v3 Lists API's memberships endpoint. Used for CLIENT-SIDE exclusion,
    since HubSpot's Search API has no 'is/is not a member of list N'
    contact-property filter to express "Classic List Membership is none
    of X" directly. Returns a set of string contact IDs.
    NOTE: because exclusion happens client-side after the fact, any block
    using this can't trust the Search API's own 'total' field (it doesn't
    know about the exclusion) - see fetch_contact_records_capped below,
    which always fully paginates and counts post-exclusion records in
    Python whenever exclude_ids is non-empty."""
    headers = {"Authorization": f"Bearer {token}"}
    endpoint = f"https://api.hubapi.com/crm/v3/lists/{list_id}/memberships"
    ids = set()
    after = None
    while True:
        params = {"limit": 250}
        if after:
            params["after"] = after
        resp = request_with_retry("GET", endpoint, headers=headers, params=params)
        data = resp.json()
        for rec in data.get("results", []):
            rid = rec.get("recordId")
            if rid is not None:
                ids.add(str(rid))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    print(f"Fetched {len(ids)} contact IDs currently in list {list_id}.")
    return ids


def fetch_active_owners(token):
    """Real HubSpot Owners API roster (active/non-archived users only),
    per your instruction - shared by both the Meetings and Calls blocks
    since owner IDs are global across engagement objects. Returns
    {owner_id: display_name}."""
    headers = {"Authorization": f"Bearer {token}"}
    owners = {}
    after = None
    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after
        resp = request_with_retry("GET", OWNERS_ENDPOINT, headers=headers, params=params)
        data = resp.json()
        for o in data.get("results", []):
            if o.get("archived"):
                continue
            name = " ".join(filter(None, [o.get("firstName"), o.get("lastName")])).strip()
            owners[o["id"]] = name or o.get("email") or o["id"]
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    print(f"Fetched {len(owners)} active HubSpot owners.")
    return owners


def normalize_owner_name(name):
    return " ".join((name or "").split()).lower()


def build_roster_from_recent_window(token, filter_property, display_property, today, window_days=ROSTER_WINDOW_DAYS):
    """UNCHANGED from the original Leads script - see original docstring."""
    window_start = today - timedelta(days=window_days)
    start_ms = utc_day_bounds_ms(window_start.year, window_start.month, window_start.day)
    end_ms = utc_day_bounds_ms(today.year, today.month, today.day, end_of_day=True)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = [
        {"propertyName": filter_property, "operator": "HAS_PROPERTY"},
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "GTE", "value": start_ms},
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "LTE", "value": end_ms},
    ]
    raw_name_counts = {}
    after = None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": [display_property], "limit": 100}
        if after:
            body["after"] = after
        resp = request_with_retry("POST", SEARCH_ENDPOINT, headers=headers, json=body)
        data = resp.json()
        for c in data.get("results", []):
            raw_name = (c.get("properties", {}) or {}).get(display_property)
            raw_name = raw_name.strip() if raw_name else ""
            if raw_name:
                raw_name_counts[raw_name] = raw_name_counts.get(raw_name, 0) + 1
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break

    grouped = {}
    for raw, count in raw_name_counts.items():
        norm = normalize_owner_name(raw)
        grouped.setdefault(norm, {})[raw] = grouped.setdefault(norm, {}).get(raw, 0) + count

    roster = {}
    for norm, variants in grouped.items():
        canonical = max(variants.items(), key=lambda kv: kv[1])[0]
        roster[norm] = canonical

    print(f"Built roster from last {window_days} days ({window_start} to {today}): "
          f"{len(roster)} distinct owners with real lead activity.")
    return roster


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def to_epoch_ms(dt):
    return int(dt.timestamp() * 1000)


def utc_day_bounds_ms(year, month, day, end_of_day=False):
    """leconnex_create_date is a HubSpot 'date' (date-only) property, stored
    at midnight UTC regardless of account timezone. UNCHANGED - only used
    by the Leads block."""
    naive = datetime(year, month, day, tzinfo=dt_timezone.utc)
    ms = to_epoch_ms(naive)
    if end_of_day:
        ms += (24 * 60 * 60 * 1000 - 1)
    return ms


def local_tz_bounds_ms(start_date, end_date, tz_name):
    """For real timestamp properties (meeting/call Activity date, deal
    Closed won date), where the calendar day a timestamp falls into
    depends on timezone. Converts local midnight-to-midnight (in tz_name)
    into UTC epoch ms, handling DST correctly via pytz.localize()."""
    tz = pytz.timezone(tz_name)
    start_local = tz.localize(datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0))
    end_local = tz.localize(datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, 999000))
    start_ms = int(start_local.astimezone(dt_timezone.utc).timestamp() * 1000)
    end_ms = int(end_local.astimezone(dt_timezone.utc).timestamp() * 1000)
    return start_ms, end_ms


def local_today():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz).date()


def sunday_on_or_before(d):
    offset = (d.weekday() - 6) % 7
    return d - timedelta(days=offset)


def month_last_day(year, month):
    return calendar.monthrange(year, month)[1]


def fmt_week_label(week_start, week_end):
    return f"{week_start.month}/{week_start.day}-{week_end.month}/{week_end.day}"


# ---------------------------------------------------------------------------
# Period tree construction (shared by every metric block - built ONCE)
# ---------------------------------------------------------------------------

class Period:
    """One column: a label + calendar start/end date + UTC-midnight
    [start_ms, end_ms] (used by the Leads block only) + a 'live' flag."""
    __slots__ = ("label", "start_date", "end_date", "start_ms", "end_ms", "live")

    def __init__(self, label, start_date, end_date, live):
        self.label = label
        self.start_date = start_date
        self.end_date = end_date
        self.start_ms = utc_day_bounds_ms(start_date.year, start_date.month, start_date.day)
        self.end_ms = utc_day_bounds_ms(end_date.year, end_date.month, end_date.day, end_of_day=True)
        self.live = live


def build_weeks(anchor_start_date, last_completed_week_end):
    first_week_start = sunday_on_or_before(anchor_start_date)
    weeks = []
    cursor = first_week_start
    while cursor <= last_completed_week_end:
        week_end = cursor + timedelta(days=6)
        weeks.append((cursor, week_end))
        cursor = cursor + timedelta(days=7)
    return weeks


def assign_week_to_month(week_start, week_end):
    counts = {}
    d = week_start
    while d <= week_end:
        key = (d.year, d.month)
        counts[key] = counts.get(key, 0) + 1
        d += timedelta(days=1)
    return max(counts.items(), key=lambda kv: kv[1])[0]


def build_period_tree(today):
    anchor_start_date = datetime(ANCHOR_START_YEAR, ANCHOR_START_MONTH, 1).date()
    current_year, current_month = today.year, today.month

    in_progress_week_start = sunday_on_or_before(today)
    last_completed_week_start = in_progress_week_start - timedelta(days=7)
    last_completed_week_end = in_progress_week_start - timedelta(days=1)

    weeks = build_weeks(anchor_start_date, last_completed_week_end)

    buckets = {}
    order = []
    for week_start, week_end in weeks:
        key = assign_week_to_month(week_start, week_end)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append((week_start, week_end))

    this_week_start = last_completed_week_start
    this_week_end = last_completed_week_end

    year_blocks = []
    years_seen = sorted(set(y for y, m in order))
    for year in years_seen:
        months_in_year = [key for key in order if key[0] == year]
        month_dicts = []
        for (y, m) in months_in_year:
            week_periods = []
            for week_start, week_end in buckets[(y, m)]:
                is_live = (week_start == this_week_start and week_end == this_week_end)
                week_periods.append(Period(fmt_week_label(week_start, week_end), week_start, week_end, is_live))

            is_current_month = (y == current_year and m == current_month)
            month_end_date = today if is_current_month else datetime(y, m, month_last_day(y, m)).date()
            month_label = f"{calendar.month_abbr[m]} {y}"
            month_total = Period(f"{month_label} Total", datetime(y, m, 1).date(), month_end_date, live=is_current_month)
            month_dicts.append({"label": month_label, "weeks": week_periods, "month_total": month_total})

        is_current_year = (year == current_year)
        year_end_date = today if is_current_year else datetime(year, 12, 31).date()
        year_total_label = f"{year} YTD" if is_current_year else f"{year} Total"
        year_total = Period(year_total_label, datetime(year, 1, 1).date(), year_end_date, live=is_current_year)

        year_blocks.append({"year": year, "year_total": year_total, "months": month_dicts})

    ly_year, ly_month = (current_year - 1, current_month)
    ly_month_end = datetime(ly_year, ly_month, month_last_day(ly_year, ly_month)).date()
    ly_month_period = Period(f"LY Month ({calendar.month_abbr[ly_month]} {ly_year})", datetime(ly_year, ly_month, 1).date(), ly_month_end, live=False)
    current_month_period = Period(f"Current Month ({calendar.month_abbr[current_month]} {current_year})", datetime(current_year, current_month, 1).date(), today, live=True)
    previous_week_period = Period(f"Previous Week ({fmt_week_label(this_week_start, this_week_end)})", this_week_start, this_week_end, live=False)
    current_week_running_period = Period(
        f"Current Week ({fmt_week_label(in_progress_week_start, in_progress_week_start + timedelta(days=6))})",
        in_progress_week_start, today, live=True,
    )
    quick_glance = [ly_month_period, current_month_period, previous_week_period, current_week_running_period]

    return quick_glance, year_blocks


def flatten_periods(quick_glance, year_blocks):
    flat = list(quick_glance)
    for yb in year_blocks:
        for month in yb["months"]:
            flat.extend(month["weeks"])
            flat.append(month["month_total"])
        flat.append(yb["year_total"])
    return flat


# ---------------------------------------------------------------------------
# HubSpot fetch + tally - LEADS (contacts object) - UNCHANGED
# ---------------------------------------------------------------------------

def _fetch_owner_tally_single(token, filter_property, display_property, start_ms, end_ms, owner_roster):
    """One direct query + full pagination for a range already known to be
    under the cap. This is the exact original fetch_owner_tally body,
    unchanged - do not call directly, use fetch_owner_tally."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = [
        {"propertyName": filter_property, "operator": "HAS_PROPERTY"},
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "GTE", "value": start_ms},
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "LTE", "value": end_ms},
    ]
    tally = {}
    after = None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": [display_property], "limit": 100}
        if after:
            body["after"] = after
        resp = request_with_retry("POST", SEARCH_ENDPOINT, headers=headers, json=body)
        data = resp.json()
        for c in data.get("results", []):
            raw_name = (c.get("properties", {}) or {}).get(display_property)
            raw_name = raw_name.strip() if raw_name else ""
            if not raw_name:
                bucket = NO_VALUE_LABEL
            else:
                bucket = owner_roster.get(normalize_owner_name(raw_name), OTHERS_LABEL)
            tally[bucket] = tally.get(bucket, 0) + 1
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return tally


def fetch_owner_tally(token, filter_property, display_property, start_ms, end_ms, owner_roster, known_total=None):
    """Same as before, now with a 10k-cap safety net: below the cap this
    returns exactly what _fetch_owner_tally_single (the original,
    unmodified function body) returns - nothing changes for any range
    that isn't near the cap. Only once a range is at/over
    MAX_RESULTS_PER_QUERY does it split the range in half and recurse,
    merging the two tallies, instead of erroring out or silently
    truncating."""
    total = known_total if known_total is not None else fetch_total_count(token, filter_property, start_ms, end_ms)
    if total > MAX_RESULTS_PER_QUERY and end_ms > start_ms:
        mid_ms = start_ms + (end_ms - start_ms) // 2
        print(f"  -> range has ~{total} results (over the {MAX_RESULTS_PER_QUERY} cap) - splitting into 2 sub-ranges")
        left = fetch_owner_tally(token, filter_property, display_property, start_ms, mid_ms, owner_roster)
        right = fetch_owner_tally(token, filter_property, display_property, mid_ms + 1, end_ms, owner_roster)
        merged = dict(left)
        for k, v in right.items():
            merged[k] = merged.get(k, 0) + v
        return merged
    return _fetch_owner_tally_single(token, filter_property, display_property, start_ms, end_ms, owner_roster)


def _fetch_total_count_single(token, filter_property, start_ms, end_ms):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = [
        {"propertyName": filter_property, "operator": "HAS_PROPERTY"},
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "GTE", "value": start_ms},
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "LTE", "value": end_ms},
    ]
    body = {"filterGroups": [{"filters": filters}], "properties": [], "limit": 1}
    resp = request_with_retry("POST", SEARCH_ENDPOINT, headers=headers, json=body)
    return resp.json().get("total", 0)


def fetch_total_count(token, filter_property, start_ms, end_ms):
    """Accurate total even once a range exceeds the cap: a single query's
    'total' field appears to be capped at the same ~10,000 as pagination,
    so a raw total at/near the cap can't be trusted on its own - split and
    sum recursively until each sub-range reports comfortably under it.
    Below the cap this returns exactly what it always did."""
    raw_total = _fetch_total_count_single(token, filter_property, start_ms, end_ms)
    if raw_total < MAX_RESULTS_PER_QUERY or end_ms <= start_ms:
        return raw_total
    mid_ms = start_ms + (end_ms - start_ms) // 2
    left = fetch_total_count(token, filter_property, start_ms, mid_ms)
    right = fetch_total_count(token, filter_property, mid_ms + 1, end_ms)
    return left + right


def fetch_period_live(period, token, filter_property, display_property, owner_roster):
    """Same fetch behavior as before. owners_seen is no longer taken/mutated
    here - it used to be updated inline, which is unsafe once multiple
    weeks are fetched concurrently from different threads. The caller
    (fetch_metric_periods) now updates it once, after each period's result
    comes back, in the main thread."""
    total = fetch_total_count(token, filter_property, period.start_ms, period.end_ms)
    tally = fetch_owner_tally(token, filter_property, display_property, period.start_ms, period.end_ms, owner_roster, known_total=total)
    print(f"{period.label:<28} [leads]    fetched live - {len(tally)} owner buckets, {total} total")
    return tally, total


# ---------------------------------------------------------------------------
# HubSpot fetch + tally - MEETINGS / CALLS (engagement objects) - UNCHANGED
# ---------------------------------------------------------------------------

def build_engagement_filters(date_property, start_ms, end_ms, extra_filters=None):
    filters = [
        {"propertyName": date_property, "operator": "GTE", "value": start_ms},
        {"propertyName": date_property, "operator": "LTE", "value": end_ms},
    ]
    if extra_filters:
        filters.extend(extra_filters)
    return filters


def _fetch_engagement_owner_tally_single(token, object_type, date_property, owner_property, start_ms, end_ms, owners_map, extra_filters):
    """One direct query + full pagination for a range already known to be
    under the cap. Do not call directly - use fetch_engagement_owner_tally."""
    endpoint = f"https://api.hubapi.com/crm/v3/objects/{object_type}/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = build_engagement_filters(date_property, start_ms, end_ms, extra_filters)
    tally = {}
    after = None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": [owner_property], "limit": 100}
        if after:
            body["after"] = after
        resp = request_with_retry("POST", endpoint, headers=headers, json=body)
        data = resp.json()
        for rec in data.get("results", []):
            owner_id = (rec.get("properties", {}) or {}).get(owner_property)
            if not owner_id:
                bucket = NO_VALUE_LABEL
            else:
                bucket = owners_map.get(owner_id, OTHERS_LABEL)
            tally[bucket] = tally.get(bucket, 0) + 1
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return tally


def fetch_engagement_owner_tally(token, object_type, date_property, owner_property, start_ms, end_ms, owners_map, extra_filters=None, known_total=None):
    """Same shape/bucketing as before (blank owner -> NO_VALUE_LABEL,
    owner ID not in the active roster -> OTHERS_LABEL, matched ->
    canonical name), but transparently splits the date range in half and
    recurses (merging tallies) whenever it's at/over HubSpot's ~10,000
    -result search cap."""
    total = known_total if known_total is not None else fetch_engagement_total_count(token, object_type, date_property, start_ms, end_ms, extra_filters)
    if total > MAX_RESULTS_PER_QUERY and end_ms > start_ms:
        mid_ms = start_ms + (end_ms - start_ms) // 2
        print(f"  -> range has ~{total} results (over the {MAX_RESULTS_PER_QUERY} cap) - splitting into 2 sub-ranges")
        left = fetch_engagement_owner_tally(token, object_type, date_property, owner_property, start_ms, mid_ms, owners_map, extra_filters)
        right = fetch_engagement_owner_tally(token, object_type, date_property, owner_property, mid_ms + 1, end_ms, owners_map, extra_filters)
        merged = dict(left)
        for k, v in right.items():
            merged[k] = merged.get(k, 0) + v
        return merged
    return _fetch_engagement_owner_tally_single(token, object_type, date_property, owner_property, start_ms, end_ms, owners_map, extra_filters)


def _fetch_engagement_total_count_single(token, object_type, date_property, start_ms, end_ms, extra_filters):
    endpoint = f"https://api.hubapi.com/crm/v3/objects/{object_type}/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = build_engagement_filters(date_property, start_ms, end_ms, extra_filters)
    body = {"filterGroups": [{"filters": filters}], "properties": [], "limit": 1}
    resp = request_with_retry("POST", endpoint, headers=headers, json=body)
    return resp.json().get("total", 0)


def fetch_engagement_total_count(token, object_type, date_property, start_ms, end_ms, extra_filters=None):
    """Accurate total even once a range exceeds the cap - see
    fetch_total_count's docstring for why a raw total near the cap can't
    be trusted on its own. Below the cap this returns exactly what it
    always did."""
    raw_total = _fetch_engagement_total_count_single(token, object_type, date_property, start_ms, end_ms, extra_filters)
    if raw_total < MAX_RESULTS_PER_QUERY or end_ms <= start_ms:
        return raw_total
    mid_ms = start_ms + (end_ms - start_ms) // 2
    left = fetch_engagement_total_count(token, object_type, date_property, start_ms, mid_ms, extra_filters)
    right = fetch_engagement_total_count(token, object_type, date_property, mid_ms + 1, end_ms, extra_filters)
    return left + right


def fetch_period_live_engagement(period, token, object_type, date_property, owner_property, owners_map, extra_filters, tz_name):
    """Same fetch behavior as before. owners_seen is no longer taken/
    mutated here, for the same thread-safety reason as fetch_period_live -
    see that function's docstring."""
    start_ms, end_ms = local_tz_bounds_ms(period.start_date, period.end_date, tz_name)
    total = fetch_engagement_total_count(token, object_type, date_property, start_ms, end_ms, extra_filters)
    tally = fetch_engagement_owner_tally(token, object_type, date_property, owner_property, start_ms, end_ms, owners_map, extra_filters, known_total=total)
    print(f"{period.label:<28} [{object_type:<8}] fetched live - {len(tally)} owner buckets, {total} total")
    return tally, total


# ---------------------------------------------------------------------------
# HubSpot fetch + tally - DEALS / Sales # + Sales $ (+ New Business,
# Renewals, Old-Lead Sales - all reuse this exact same fetch machinery,
# just with different dealstage_values / extra_filters arguments)
# ---------------------------------------------------------------------------
# Sales # (deal count) and Sales $ (summed amount) are two views of the
# EXACT SAME set of closed-won deals for a period, so they're fetched
# together from one paginated pass rather than two separate queries -
# querying twice would double the API calls for no benefit, since the
# records are identical either way. Unlike every count-only block above,
# HubSpot's Search API has no native SUM aggregate, so getting an accurate
# dollar total is only possible by fully paginating and summing client-
# side - there's no cheap total-field shortcut available for the dollar
# figure the way there is for a count. The COUNT total shown in the sheet
# is likewise just derived from that same full pagination (every matching
# record is enumerated exactly once), not from a separate probe call -
# since we already have to walk every record for the dollar sum, a
# redundant limit=1 count probe would buy nothing. A cheap limit=1 probe
# IS still used, but only internally, to decide whether a range needs to
# be pre-split before committing to a full unchunked pagination pass (see
# fetch_deal_tallies) - same purpose as fetch_total_count/
# fetch_engagement_total_count elsewhere in this script.
#
# extra_filters is a NEW optional parameter threaded through
# build_deal_filters / fetch_deal_count_probe / _fetch_deal_tallies_single /
# fetch_deal_tallies / fetch_deal_period_live, defaulting to None
# everywhere. The existing combined Sales #/$ block's call sites never
# pass it, so their behavior is byte-for-byte unchanged - it exists only
# so the new Old-Lead-Sales block can add its one extra dropdown filter
# without duplicating this entire fetch stack.
# ---------------------------------------------------------------------------

def build_deal_filters(closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, extra_filters=None):
    filters = [
        {"propertyName": dealstage_property, "operator": "IN", "values": dealstage_values},
        {"propertyName": closed_won_date_property, "operator": "GTE", "value": start_ms},
        {"propertyName": closed_won_date_property, "operator": "LTE", "value": end_ms},
    ]
    if extra_filters:
        filters.extend(extra_filters)
    return filters


def fetch_deal_count_probe(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, extra_filters=None):
    """Cheap limit=1 total-field probe, used ONLY to decide whether a
    range needs pre-splitting before a full pagination pass - not used as
    the displayed count (see module note above for why)."""
    endpoint = "https://api.hubapi.com/crm/v3/objects/deals/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = build_deal_filters(closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, extra_filters)
    body = {"filterGroups": [{"filters": filters}], "properties": [], "limit": 1}
    resp = request_with_retry("POST", endpoint, headers=headers, json=body)
    return resp.json().get("total", 0)


def _fetch_deal_tallies_single(token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, start_ms, end_ms, owners_map, extra_filters=None):
    """One direct query + full pagination for a range already known to be
    under the cap - builds BOTH the count tally and the dollar tally from
    the same records. Do not call directly - use fetch_deal_tallies."""
    endpoint = "https://api.hubapi.com/crm/v3/objects/deals/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = build_deal_filters(closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, extra_filters)
    count_tally, dollar_tally = {}, {}
    after = None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": [amount_property, owner_property], "limit": 100}
        if after:
            body["after"] = after
        resp = request_with_retry("POST", endpoint, headers=headers, json=body)
        data = resp.json()
        for rec in data.get("results", []):
            props = rec.get("properties", {}) or {}
            owner_id = props.get(owner_property)
            bucket = owners_map.get(owner_id, OTHERS_LABEL) if owner_id else NO_VALUE_LABEL
            amt = float(props.get(amount_property) or 0)
            count_tally[bucket] = count_tally.get(bucket, 0) + 1
            dollar_tally[bucket] = dollar_tally.get(bucket, 0) + amt
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return count_tally, dollar_tally


def fetch_deal_tallies(token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, start_ms, end_ms, owners_map, known_probe_total=None, extra_filters=None):
    """Same 10k-cap split-and-merge safety net as every other block,
    applied to BOTH tallies at once since they share one paginated record
    set. Below the cap, returns exactly what _fetch_deal_tallies_single
    returns."""
    probe_total = known_probe_total if known_probe_total is not None else fetch_deal_count_probe(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, extra_filters)
    if probe_total > MAX_RESULTS_PER_QUERY and end_ms > start_ms:
        mid_ms = start_ms + (end_ms - start_ms) // 2
        print(f"  -> range has ~{probe_total} deals (over the {MAX_RESULTS_PER_QUERY} cap) - splitting into 2 sub-ranges")
        left_count, left_dollar = fetch_deal_tallies(token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, start_ms, mid_ms, owners_map, extra_filters=extra_filters)
        right_count, right_dollar = fetch_deal_tallies(token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, mid_ms + 1, end_ms, owners_map, extra_filters=extra_filters)
        merged_count = dict(left_count)
        for k, v in right_count.items():
            merged_count[k] = merged_count.get(k, 0) + v
        merged_dollar = dict(left_dollar)
        for k, v in right_dollar.items():
            merged_dollar[k] = merged_dollar.get(k, 0) + v
        return merged_count, merged_dollar
    return _fetch_deal_tallies_single(token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, start_ms, end_ms, owners_map, extra_filters)


def fetch_deal_period_live(period, token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, owners_map, tz_name, extra_filters=None):
    """Returns FOUR values (count_tally, dollar_tally, count_total,
    dollar_total) instead of the (tally, total) pair every other block's
    fetch_fn returns - see fetch_deal_metric_periods, which is the deals-
    aware counterpart to fetch_metric_periods that knows how to walk this
    4-tuple shape. extra_filters (NEW, optional, default None) is passed
    straight through to fetch_deal_tallies - the existing combined Sales
    #/$ block never sets it, so its results are unaffected; the new
    Old-Lead-Sales block passes one extra filter here."""
    start_ms, end_ms = local_tz_bounds_ms(period.start_date, period.end_date, tz_name)
    count_tally, dollar_tally = fetch_deal_tallies(token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, start_ms, end_ms, owners_map, extra_filters=extra_filters)
    count_total = sum(count_tally.values())
    dollar_total = sum(dollar_tally.values())
    print(f"{period.label:<28} [deals   ] fetched live - {len(count_tally)} owner buckets, {count_total} deals, ${dollar_total:,.2f}")
    return count_tally, dollar_tally, count_total, dollar_total


# ---------------------------------------------------------------------------
# NEW (round 5): deal-search multi-branch engine, for Google Sales / AI
# Sales - the deals-object counterpart of the contact multi-branch engine
# below (fetch_contact_records_multi_branch etc.), needed because AI
# Sales is an OR across two deal-level conditions (source contains 'AI'
# OR Inferred Landing Page contains 'chatgpt') and build_deal_filters'
# extra_filters is AND-only. Google Sales only ever uses a single branch,
# so it costs exactly what fetch_deal_period_live already costs.
# ---------------------------------------------------------------------------

def _fetch_deal_records_single(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, properties, extra_filters=None):
    """NEW - full pagination for ONE deal-search branch (a single
    filterGroup) already known to be under the cap - returns the raw
    list of matching deal records (id + properties), not yet tallied.
    Do not call directly for a range that might be over the 10k cap -
    use fetch_deal_records_capped. Mirrors _fetch_contacts_paginated's
    role for the contact multi-branch engine below, but for deals."""
    endpoint = "https://api.hubapi.com/crm/v3/objects/deals/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    filters = build_deal_filters(closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, extra_filters)
    records = []
    after = None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": properties, "limit": 100}
        if after:
            body["after"] = after
        resp = request_with_retry("POST", endpoint, headers=headers, json=body)
        data = resp.json()
        records.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return records


def fetch_deal_records_capped(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, properties, extra_filters=None, known_probe_total=None):
    """NEW - same 10k-cap split-and-merge safety net as every other fetch
    function in this script, for ONE deal-search branch. Below the cap,
    returns exactly what _fetch_deal_records_single returns."""
    probe_total = known_probe_total if known_probe_total is not None else fetch_deal_count_probe(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, extra_filters)
    if probe_total > MAX_RESULTS_PER_QUERY and end_ms > start_ms:
        mid_ms = start_ms + (end_ms - start_ms) // 2
        print(f"  -> range has ~{probe_total} deals (over the {MAX_RESULTS_PER_QUERY} cap) - splitting into 2 sub-ranges")
        left = fetch_deal_records_capped(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, mid_ms, properties, extra_filters)
        right = fetch_deal_records_capped(token, closed_won_date_property, dealstage_property, dealstage_values, mid_ms + 1, end_ms, properties, extra_filters)
        return left + right
    return _fetch_deal_records_single(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, properties, extra_filters)


def fetch_deal_records_multi_branch(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, properties, extra_filters_branches):
    """NEW - issues one SEPARATE HubSpot deal-search request per
    extra_filters branch (each branch AND'd with the shared closed-won-
    stage + date-range condition) and merges the resulting deals by ID,
    so a deal matching more than one branch is only counted once - the
    deals-object counterpart of fetch_contact_records_multi_branch below.
    A single-branch call (Google Sales) is just one request, identical
    in cost to fetch_deal_tallies."""
    seen_ids = set()
    merged = []
    for extra_filters in extra_filters_branches:
        records = fetch_deal_records_capped(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, properties, extra_filters)
        for r in records:
            rid = r.get("id")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            merged.append(r)
    return merged


def _tally_deals_by_owner(records, amount_property, owner_property, owners_map):
    """NEW - same bucketing rule as _fetch_deal_tallies_single above
    (blank owner -> NO_VALUE_LABEL, owner ID not in the active roster ->
    OTHERS_LABEL, matched -> canonical name), operating on an
    already-fetched/merged list of deal records instead of doing its own
    pagination."""
    count_tally, dollar_tally = {}, {}
    for rec in records:
        props = rec.get("properties", {}) or {}
        owner_id = props.get(owner_property)
        bucket = owners_map.get(owner_id, OTHERS_LABEL) if owner_id else NO_VALUE_LABEL
        amt = float(props.get(amount_property) or 0)
        count_tally[bucket] = count_tally.get(bucket, 0) + 1
        dollar_tally[bucket] = dollar_tally.get(bucket, 0) + amt
    return count_tally, dollar_tally


def fetch_source_deal_period_live(period, token, closed_won_date_property, dealstage_property, dealstage_values, amount_property, owner_property, owners_map, tz_name, extra_filters_branches):
    """NEW - period-live fetch for the new Google Sales / AI Sales
    blocks: same 4-tuple return shape as fetch_deal_period_live (so it
    plugs into the existing fetch_deal_metric_periods walker with ZERO
    changes to that function), but supports an OR across multiple
    extra_filters branches via fetch_deal_records_multi_branch above -
    the single-branch case (Google Sales) costs exactly what
    fetch_deal_period_live already costs."""
    start_ms, end_ms = local_tz_bounds_ms(period.start_date, period.end_date, tz_name)
    records = fetch_deal_records_multi_branch(token, closed_won_date_property, dealstage_property, dealstage_values, start_ms, end_ms, [amount_property, owner_property], extra_filters_branches)
    count_tally, dollar_tally = _tally_deals_by_owner(records, amount_property, owner_property, owners_map)
    count_total = sum(count_tally.values())
    dollar_total = sum(dollar_tally.values())
    print(f"{period.label:<28} [src-deal] fetched live - {len(count_tally)} owner buckets, {count_total} deals, ${dollar_total:,.2f}")
    return count_tally, dollar_tally, count_total, dollar_total


# ---------------------------------------------------------------------------
# NEW: generic contact-search engine for the round-2 blocks (Google Leads,
# AI Leads, Appt Set, Appt Set High/Low Income, New Lead (no appt), Appt
# Set Meetings Completed, MM Recruits, MM Recruits - Samantha).
#
# These all still search the /crm/v3/objects/contacts/search endpoint like
# the original Leads block, but need two things the original single-
# filterGroup fetch_owner_tally()/fetch_total_count() functions above
# don't support, so rather than bolt more optional params onto those
# (which are explicitly documented as UNCHANGED) this is a parallel,
# separate engine:
#   1. MULTIPLE filterGroups (OR'd together) - needed to express e.g.
#      "Source* contains AI  OR  Inferred Landing Page contains chatgpt"
#      as (branch1) OR (branch2), since a single filterGroup ANDs all its
#      filters together and can't express an OR on its own.
#   2. CLIENT-SIDE exclusion by contact ID - needed for "Classic List
#      Membership is none of X", which has no Search-API property filter
#      (see fetch_list_membership_ids above). Because exclusion happens
#      after HubSpot's own count, any block using exclude_ids must fully
#      paginate and count in Python - the 'total' field from HubSpot is
#      pre-exclusion and can't be trusted (same situation as the Sales $
#      block's dollar sums, which also can't use a cheap total-field
#      shortcut).
# ---------------------------------------------------------------------------

def build_create_date_range_filters(start_ms, end_ms, compact=False):
    """FIX (A) - returns the create-date range portion of a branch.

    compact=False (default, used by every builder that has filter-slot
    headroom): the original two-filter GTE + LTE pair, byte-for-byte
    identical to what every other block in this script emits.

    compact=True: ONE inclusive BETWEEN filter instead, for branches that
    would otherwise exceed MAX_FILTERS_PER_GROUP. HubSpot's BETWEEN is
    inclusive of BOTH bounds, so it matches exactly the same record set as
    the GTE/LTE pair - it just costs one filter slot instead of two.

    NOTE: anything emitting the compact form MUST be splittable by
    _rewrite_date_bounds below, which was taught about BETWEEN in fix (B)."""
    if compact:
        return [{
            "propertyName": CREATE_DATE_PROPERTY,
            "operator": "BETWEEN",
            "value": start_ms,
            "highValue": end_ms,
        }]
    return [
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "GTE", "value": start_ms},
        {"propertyName": CREATE_DATE_PROPERTY, "operator": "LTE", "value": end_ms},
    ]


def fetch_contact_probe_total(token, filters):
    """Cheap limit=1 total-field probe for a SINGLE branch (one AND'd
    filters list, wrapped in exactly one filterGroup) - used ONLY to
    decide whether a date range needs pre-splitting before a full
    pagination pass, same purpose as fetch_deal_count_probe above. NOT
    trustworthy as a final count once client-side ID exclusion is in play
    (see module note below) - the caller always re-derives the real count
    from full pagination."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"filterGroups": [{"filters": filters}], "properties": [], "limit": 1}
    resp = request_with_retry("POST", SEARCH_ENDPOINT, headers=headers, json=body)
    return resp.json().get("total", 0)


def _rewrite_date_bounds(filters, date_property, start_ms, end_ms):
    """Returns a new filters list (a single branch) with every date filter
    on date_property re-pointed at the given start_ms/end_ms - used to
    split one branch into two narrower date sub-ranges.

    FIX (B): handles the compact BETWEEN form as well as the original
    GTE/LTE pair, so a range that trips the 10k-cap splitter doesn't run
    both halves against the original full range and double-count."""
    new_filters = []
    for f in filters:
        if f.get("propertyName") == date_property and f.get("operator") == "BETWEEN":
            new_filters.append({**f, "value": start_ms, "highValue": end_ms})
        elif f.get("propertyName") == date_property and f.get("operator") == "GTE":
            new_filters.append({**f, "value": start_ms})
        elif f.get("propertyName") == date_property and f.get("operator") == "LTE":
            new_filters.append({**f, "value": end_ms})
        else:
            new_filters.append(f)
    return new_filters


def _fetch_contacts_paginated(token, filters, properties, exclude_ids=None):
    """Full pagination for ONE branch (a single filters list, wrapped in
    exactly one filterGroup) already known to be under the cap - returns
    the list of matching contact records (each a dict with 'id' and
    'properties'), skipping any whose ID is in exclude_ids. Do not call
    directly for a range that might be over the 10k cap - use
    fetch_contact_records_capped."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    records = []
    after = None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": properties, "limit": 100}
        if after:
            body["after"] = after
        resp = request_with_retry("POST", SEARCH_ENDPOINT, headers=headers, json=body)
        data = resp.json()
        for c in data.get("results", []):
            if exclude_ids and c.get("id") in exclude_ids:
                continue
            records.append(c)
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return records


def fetch_contact_records_capped(token, filters, properties, date_property, start_ms, end_ms, exclude_ids=None, known_probe_total=None):
    """Same 10k-cap split-and-merge safety net as every other fetch
    function in this script, for ONE branch (a single filters list - one
    filterGroup, one HubSpot request). Below the cap, returns exactly
    what _fetch_contacts_paginated returns."""
    probe_total = known_probe_total if known_probe_total is not None else fetch_contact_probe_total(token, filters)
    if probe_total > MAX_RESULTS_PER_QUERY and end_ms > start_ms:
        mid_ms = start_ms + (end_ms - start_ms) // 2
        print(f"  -> range has ~{probe_total} contacts (over the {MAX_RESULTS_PER_QUERY} cap) - splitting into 2 sub-ranges")
        left_filters = _rewrite_date_bounds(filters, date_property, start_ms, mid_ms)
        right_filters = _rewrite_date_bounds(filters, date_property, mid_ms + 1, end_ms)
        left = fetch_contact_records_capped(token, left_filters, properties, date_property, start_ms, mid_ms, exclude_ids)
        right = fetch_contact_records_capped(token, right_filters, properties, date_property, mid_ms + 1, end_ms, exclude_ids)
        return left + right
    return _fetch_contacts_paginated(token, filters, properties, exclude_ids)


def fetch_contact_records_multi_branch(token, branches, properties, date_property, start_ms, end_ms, exclude_ids=None):
    """NEW - issues one SEPARATE HubSpot request per branch and merges the
    results by contact ID, so a contact that happens to match more than
    one branch is only counted once. For builders with only one branch
    (Appt Set, MM Recruits, etc.) this is just one request, identical in
    cost to before.

    FIX (C): every branch is validated against MAX_FILTERS_PER_GROUP
    BEFORE any request goes out, so an over-cap branch fails instantly
    with the offending filter list printed, instead of a bare 400 deep
    into a long run."""
    for filters in branches:
        if len(filters) > MAX_FILTERS_PER_GROUP:
            offending = "\n".join(f"  - {f}" for f in filters)
            sys.exit(
                f"ERROR: a search branch has {len(filters)} filters, over HubSpot's max of "
                f"{MAX_FILTERS_PER_GROUP} per filterGroup. HubSpot would reject this with a 400 "
                f"VALIDATION_ERROR ('too many filters per filter group').\nOffending branch:\n{offending}\n"
                f"Fix by collapsing a GTE/LTE date pair into one BETWEEN filter "
                f"(build_create_date_range_filters(..., compact=True)), or by dropping a cheap "
                f"condition from the query and applying it client-side after fetching."
            )

    seen_ids = set()
    merged = []
    for filters in branches:
        records = fetch_contact_records_capped(token, filters, properties, date_property, start_ms, end_ms, exclude_ids=exclude_ids)
        for r in records:
            rid = r.get("id")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            merged.append(r)
    return merged


def _tally_contacts_by_owner(records, display_property, owner_roster):
    """Same bucketing rule as _fetch_owner_tally_single above (blank name
    -> NO_VALUE_LABEL, name not in the roster -> OTHERS_LABEL, matched ->
    canonical roster name), just operating on an already-fetched list of
    records instead of doing its own pagination."""
    tally = {}
    for c in records:
        raw_name = (c.get("properties", {}) or {}).get(display_property)
        raw_name = raw_name.strip() if raw_name else ""
        if not raw_name:
            bucket = NO_VALUE_LABEL
        else:
            bucket = owner_roster.get(normalize_owner_name(raw_name), OTHERS_LABEL)
        tally[bucket] = tally.get(bucket, 0) + 1
    return tally


def fetch_new_contact_metric_period_live(period, token, branches_builder, display_property, owner_roster, exclude_ids=None):
    """Generic period-live fetch for every round-2 owner-broken-down
    contact metric (Google Leads, AI Leads, Appt Set, Appt Set High/Low
    Income, New Lead (no appt), Appt Set Meetings Completed, MM Recruits,
    MM Recruits - Samantha) - returns (tally, total), the same shape as
    fetch_period_live, so it plugs directly into the existing
    fetch_metric_periods() walker with zero changes to that function.
    branches_builder(start_ms, end_ms) -> a list of branches (each branch
    a plain filters list, OR'd together via separate requests - see
    fetch_contact_records_multi_branch) lets each period substitute its
    own date bounds into an otherwise-fixed filter shape (built once in
    main() via functools.partial with everything else already resolved).
    All of these round-2 metrics key off the same UTC date-only
    CREATE_DATE_PROPERTY as the original Leads block (leconnex_create_date),
    so period.start_ms/period.end_ms (already computed by Period.__init__)
    are used directly - no separate local_tz_bounds_ms conversion needed.
    NOTE: whenever exclude_ids is non-empty, 'total' here is a Python-side
    count of the post-exclusion records, not HubSpot's own 'total' field -
    see fetch_contact_records_multi_branch/_fetch_contacts_paginated for
    why."""
    branches = branches_builder(period.start_ms, period.end_ms)
    records = fetch_contact_records_multi_branch(token, branches, [display_property], CREATE_DATE_PROPERTY, period.start_ms, period.end_ms, exclude_ids=exclude_ids)
    tally = _tally_contacts_by_owner(records, display_property, owner_roster)
    total = sum(tally.values())
    print(f"{period.label:<28} [new-contact] fetched live - {len(tally)} owner buckets, {total} total")
    return tally, total


# ---------------------------------------------------------------------------
# NEW: per-metric branches_builder functions for the round-2 blocks. Each
# returns a list of BRANCHES (plain filters lists, OR'd together via
# separate requests per fetch_contact_records_multi_branch) rather than
# HubSpot filterGroup dicts. Each takes the already-resolved property
# names/values as its LEADING arguments and (start_ms, end_ms) as its
# trailing arguments, so main() fixes the leading arguments with
# functools.partial(...) once everything is resolved, and hands the
# resulting 2-arg callable to fetch_new_contact_metric_period_live as
# branches_builder.
# ---------------------------------------------------------------------------

def build_google_leads_branches(source_property, start_ms, end_ms):
    """Google Leads Assigned: Date Created in period + Source* contains
    exactly 'Google'. CONFIRMED (round 4) against the real HubSpot saved
    view - single condition, single branch, no owner/name/email/status
    conditions. FILTER COUNT: 3."""
    return [
        build_create_date_range_filters(start_ms, end_ms) + [
            {"propertyName": source_property, "operator": "CONTAINS_TOKEN", "value": GOOGLE_SOURCE_CONTAINS_VALUE},
        ]
    ]


def build_ai_leads_branches(source_property, inferred_landing_page_property, start_ms, end_ms):
    """AI/ChatGPT Leads: Date Created in period AND (Source* contains 'AI'
    OR Inferred Landing Page contains 'chatgpt'). CONFIRMED (round 4)
    against the real HubSpot saved view - two branches, each carrying its
    own copy of the date-range filter (the real view has the Date Created
    condition inside BOTH OR'd groups individually), merged/de-duped by
    fetch_contact_records_multi_branch. FILTER COUNT: 2 per branch."""
    date_filters = build_create_date_range_filters(start_ms, end_ms)
    return [
        date_filters + [{"propertyName": source_property, "operator": "CONTAINS_TOKEN", "value": AI_SOURCE_CONTAINS_VALUE}],
        date_filters + [{"propertyName": inferred_landing_page_property, "operator": "CONTAINS_TOKEN", "value": INFERRED_LANDING_PAGE_CONTAINS_VALUE}],
    ]


def build_appt_set_branches(appt_set_calc_property, start_ms, end_ms):
    """Appt Set: Date Created in period + Appointment Set Calculation = 1.
    (Classic List Membership none of 1090 is handled separately via
    exclude_ids, not as a filter here - see fetch_list_membership_ids.)
    Single branch (no OR condition needed). FILTER COUNT: 3."""
    return [
        build_create_date_range_filters(start_ms, end_ms) + [
            {"propertyName": appt_set_calc_property, "operator": "EQ", "value": APPOINTMENT_SET_CALC_TARGET_VALUE},
        ]
    ]


def build_appt_set_high_income_branches(appt_set_calc_property, income_property, start_ms, end_ms):
    """Appt Set + Income Range dropdown value is one of the confirmed
    at/above-$75k bands (see INCOME_HIGH_VALUES - pulled live from your
    portal, real dropdown option values, not a guessed numeric threshold).
    '50-100' is deliberately excluded here - see INCOME_AMBIGUOUS_VALUES.
    FILTER COUNT: 4."""
    branches = build_appt_set_branches(appt_set_calc_property, start_ms, end_ms)
    branches[0].append({"propertyName": income_property, "operator": "IN", "values": INCOME_HIGH_VALUES})
    return branches


def build_appt_set_low_income_branches(appt_set_calc_property, income_property, start_ms, end_ms):
    """Appt Set + Income Range dropdown value is one of the confirmed
    below-$75k bands (see INCOME_LOW_VALUES). '50-100' is deliberately
    excluded here too - see INCOME_AMBIGUOUS_VALUES. FILTER COUNT: 4."""
    branches = build_appt_set_branches(appt_set_calc_property, start_ms, end_ms)
    branches[0].append({"propertyName": income_property, "operator": "IN", "values": INCOME_LOW_VALUES})
    return branches


def build_new_lead_no_appt_branches(appt_set_calc_property, start_ms, end_ms):
    """New Lead (no appt) - CONFIRMED (round 4, FIX F) against the real
    HubSpot report (report 108263989): Date Created in period +
    Appointment Set Calculation is NOT EQUAL TO 1. (Classic List
    Membership none of "imported" applied separately via exclude_ids, not
    here.) The earlier EQ '1' version was identical to the Appt Set
    filter (backwards for a "no appt" metric) and badly undercounted
    (233 vs. a real report total of 566 for the same period).
    FILTER COUNT: 3."""
    return [
        build_create_date_range_filters(start_ms, end_ms) + [
            {"propertyName": appt_set_calc_property, "operator": "NEQ", "value": APPOINTMENT_SET_CALC_TARGET_VALUE},
        ]
    ]


def build_appt_set_meetings_completed_branches(appt_set_calc_property, date_met_with_property, start_ms, end_ms):
    """Appt Set Meetings Completed: Date Created in period + Date Met With
    (face-to-face) is known + Appointment Set Calculation = 1. (Classic
    List Membership none of "imported" applied via exclude_ids.)
    FILTER COUNT: 4."""
    return [
        build_create_date_range_filters(start_ms, end_ms) + [
            {"propertyName": date_met_with_property, "operator": "HAS_PROPERTY"},
            {"propertyName": appt_set_calc_property, "operator": "EQ", "value": APPOINTMENT_SET_CALC_TARGET_VALUE},
        ]
    ]


def build_mm_recruits_branches(filter_property, start_ms, end_ms):
    """MM Recruits - see the FLAG comment on MM_RECRUITS_TOTAL_ROW_LABEL
    above: this is the SAME filter as the existing Total Leads Assigned
    block (filter_property HAS_PROPERTY + create-date range only).
    FILTER COUNT: 3."""
    return [
        [{"propertyName": filter_property, "operator": "HAS_PROPERTY"}]
        + build_create_date_range_filters(start_ms, end_ms)
    ]


def build_mm_recruits_samantha_branches(filter_property, display_property, start_ms, end_ms):
    """MM Recruits, narrowed to just Samantha - same base filter as MM
    Recruits, plus a CONTAINS_TOKEN match on the display property (the
    free-text owner name field) for 'samantha'. FILTER COUNT: 4."""
    branches = build_mm_recruits_branches(filter_property, start_ms, end_ms)
    branches[0].append({"propertyName": display_property, "operator": "CONTAINS_TOKEN", "value": SAMANTHA_OWNER_NAME_CONTAINS})
    return branches


# ---------------------------------------------------------------------------
# Concurrent week fetching (per calendar month) - shared by all blocks
# ---------------------------------------------------------------------------

def fetch_weeks_concurrently(executor, weeks, fetch_fn, fetch_args):
    """Runs fetch_fn(period, *fetch_args) for every week in `weeks` (the
    4-5 weeks belonging to one calendar month) AT THE SAME TIME, via the
    shared thread pool. Returns a list of results in the same order as
    `weeks` - console print() lines from the concurrent fetches may
    interleave/print out of order, that's cosmetic only; the returned
    results are matched back to their period by position (via zip on
    `weeks` in fetch_metric_periods/fetch_deal_metric_periods), not by
    print order, so the sheet output is unaffected."""
    futures = [executor.submit(fetch_fn, period, *fetch_args) for period in weeks]
    return [f.result() for f in futures]


def fetch_metric_periods(year_blocks, quick_glance, executor, fetch_fn, fetch_args):
    """Walks the shared period tree, with weeks within each month fetched
    CONCURRENTLY (that month's whole batch at once). Month totals, year
    totals, and the quick-glance columns stay sequential. fetch_fn is
    fetch_period_live or fetch_period_live_engagement (both return
    (tally, total)). Returns (period_values, period_totals, owners_seen)."""
    period_values, period_totals, owners_seen = {}, {}, set()

    def record(period, tally, total):
        period_values[period.label] = tally
        period_totals[period.label] = total
        owners_seen.update(tally.keys())

    for yb in year_blocks:
        for month in yb["months"]:
            weeks = month["weeks"]
            if weeks:
                results = fetch_weeks_concurrently(executor, weeks, fetch_fn, fetch_args)
                for period, (tally, total) in zip(weeks, results):
                    record(period, tally, total)
            tally, total = fetch_fn(month["month_total"], *fetch_args)
            record(month["month_total"], tally, total)
        tally, total = fetch_fn(yb["year_total"], *fetch_args)
        record(yb["year_total"], tally, total)

    for period in quick_glance:
        tally, total = fetch_fn(period, *fetch_args)
        record(period, tally, total)

    return period_values, period_totals, owners_seen


def fetch_deal_metric_periods(year_blocks, quick_glance, executor, fetch_fn, fetch_args):
    """Deals counterpart to fetch_metric_periods - same walking structure,
    but fetch_fn (fetch_deal_period_live) returns FOUR values per period
    (count_tally, dollar_tally, count_total, dollar_total). Reused as-is
    for the combined Sales block AND for New Business / Renewals / Old-
    Lead-Sales - only the fetch_args tuple differs per call site."""
    count_values, count_totals = {}, {}
    dollar_values, dollar_totals = {}, {}
    owners_seen = set()

    def record(period, count_tally, dollar_tally, count_total, dollar_total):
        count_values[period.label] = count_tally
        count_totals[period.label] = count_total
        dollar_values[period.label] = dollar_tally
        dollar_totals[period.label] = dollar_total
        owners_seen.update(count_tally.keys())
        owners_seen.update(dollar_tally.keys())

    for yb in year_blocks:
        for month in yb["months"]:
            weeks = month["weeks"]
            if weeks:
                results = fetch_weeks_concurrently(executor, weeks, fetch_fn, fetch_args)
                for period, (ct, dt_, cto, dto) in zip(weeks, results):
                    record(period, ct, dt_, cto, dto)
            ct, dt_, cto, dto = fetch_fn(month["month_total"], *fetch_args)
            record(month["month_total"], ct, dt_, cto, dto)
        ct, dt_, cto, dto = fetch_fn(yb["year_total"], *fetch_args)
        record(yb["year_total"], ct, dt_, cto, dto)

    for period in quick_glance:
        ct, dt_, cto, dto = fetch_fn(period, *fetch_args)
        record(period, ct, dt_, cto, dto)

    return count_values, count_totals, dollar_values, dollar_totals, owners_seen


# ---------------------------------------------------------------------------
# NEW: Daily tab fetch machinery - one Period per calendar day instead of
# the weekly/monthly/yearly period tree above. Reuses fetch_period_live_
# engagement / fetch_deal_period_live and fetch_weeks_concurrently exactly
# as-is (both are already generic over "a list of Periods") - nothing
# above this point is touched.
# ---------------------------------------------------------------------------

DAILY_TAB_WINDOW_START = datetime(2025, 12, 28).date()  # Sunday on/before 1/1/2026 - full first week

def build_daily_period_columns(today):
    """NEW - builds BOTH the flat list of real day Periods (for fetching)
    AND the full column layout for the Daily tab's sheet (for writing),
    covering 2026: full Sunday-Saturday calendar weeks starting from the
    week containing 1/1/2026 (DAILY_TAB_WINDOW_START = 12/28/2025) through
    today, with ONE BLANK SPACER COLUMN inserted between each week for
    readability (none after the final week). Confirmed against your
    example layout: '12/28 12/29 12/30 12/31 1/1 1/2 1/3 [blank] 1/4 ...'.

    Returns (daily_periods, daily_columns):
      - daily_periods: flat list of real Period objects only (no spacers)
        - what fetch_daily_metric_periods/fetch_daily_deal_metric_periods
          actually query HubSpot for.
      - daily_columns: the full column sequence for the sheet, a mix of
        real Period objects and None (spacer) entries in display order -
        what build_daily_metric_rows/build_daily_blank_rows lay out.

    Each real Period's label is 'M/D' (no year, no leading zeros) to match
    your example - safe here since the window never repeats a month/day
    combination (it spans parts of only two adjacent calendar years)."""
    weeks = []
    cursor = DAILY_TAB_WINDOW_START
    while cursor <= today:
        week_end = min(cursor + timedelta(days=6), today)
        weeks.append((cursor, week_end))
        cursor += timedelta(days=7)

    daily_periods = []
    daily_columns = []
    for i, (week_start, week_end) in enumerate(weeks):
        d = week_start
        while d <= week_end:
            p = Period(f"{d.month}/{d.day}", d, d, live=(d == today))
            daily_periods.append(p)
            daily_columns.append(p)
            d += timedelta(days=1)
        if i < len(weeks) - 1:
            daily_columns.append(None)  # spacer column between weeks

    return daily_periods, daily_columns


def group_daily_periods_by_month(daily_periods):
    """NEW - groups the flat daily period list into ordered (year, month)
    buckets, purely so the two functions below can fetch one calendar
    month's days concurrently at a time - the same pattern
    fetch_weeks_concurrently already uses for weeks within a month."""
    buckets = {}
    order = []
    for p in daily_periods:
        key = (p.start_date.year, p.start_date.month)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(p)
    return [buckets[k] for k in order]


def fetch_daily_metric_periods(daily_periods, executor, fetch_fn, fetch_args):
    """NEW - daily counterpart to fetch_metric_periods: walks a flat list
    of day Periods (grouped by month for concurrency), no week/month/year
    roll-up. fetch_fn is fetch_period_live_engagement (returns
    (tally, total)). Returns (period_values, period_totals, owners_seen)."""
    period_values, period_totals, owners_seen = {}, {}, set()

    def record(period, tally, total):
        period_values[period.label] = tally
        period_totals[period.label] = total
        owners_seen.update(tally.keys())

    for month_days in group_daily_periods_by_month(daily_periods):
        results = fetch_weeks_concurrently(executor, month_days, fetch_fn, fetch_args)
        for period, (tally, total) in zip(month_days, results):
            record(period, tally, total)

    return period_values, period_totals, owners_seen


def fetch_daily_deal_metric_periods(daily_periods, executor, fetch_fn, fetch_args):
    """NEW - daily counterpart to fetch_deal_metric_periods, same grouping
    strategy as fetch_daily_metric_periods above. fetch_fn is
    fetch_deal_period_live (returns count_tally, dollar_tally, count_total,
    dollar_total per day) - only the count side is used by the Daily tab's
    Sales block, but all four are returned for consistency with the
    existing deal-fetch shape."""
    count_values, count_totals = {}, {}
    dollar_values, dollar_totals = {}, {}
    owners_seen = set()

    def record(period, count_tally, dollar_tally, count_total, dollar_total):
        count_values[period.label] = count_tally
        count_totals[period.label] = count_total
        dollar_values[period.label] = dollar_tally
        dollar_totals[period.label] = dollar_total
        owners_seen.update(count_tally.keys())
        owners_seen.update(dollar_tally.keys())

    for month_days in group_daily_periods_by_month(daily_periods):
        results = fetch_weeks_concurrently(executor, month_days, fetch_fn, fetch_args)
        for period, (ct, dt_, cto, dto) in zip(month_days, results):
            record(period, ct, dt_, cto, dto)

    return count_values, count_totals, dollar_values, dollar_totals, owners_seen


# ---------------------------------------------------------------------------
# NEW (round 7): freeze engine - read the previous run's sheet, and reuse
# any period that is already finished instead of re-querying HubSpot.
# ---------------------------------------------------------------------------

MASTER_FREEZABLE_BLOCK_LABELS = {
    TOTAL_ROW_LABEL, MEETINGS_TOTAL_ROW_LABEL, CALLS_TOTAL_ROW_LABEL,
    SALES_COUNT_TOTAL_ROW_LABEL, SALES_DOLLAR_TOTAL_ROW_LABEL,
    NEW_BUSINESS_COUNT_TOTAL_ROW_LABEL, NEW_BUSINESS_DOLLAR_TOTAL_ROW_LABEL,
    RENEWALS_COUNT_TOTAL_ROW_LABEL, RENEWALS_DOLLAR_TOTAL_ROW_LABEL,
    OLD_LEAD_SALES_COUNT_TOTAL_ROW_LABEL, OLD_LEAD_SALES_DOLLAR_TOTAL_ROW_LABEL,
    GOOGLE_LEADS_TOTAL_ROW_LABEL, AI_LEADS_TOTAL_ROW_LABEL,
    APPT_SET_TOTAL_ROW_LABEL, APPT_SET_HIGH_INCOME_TOTAL_ROW_LABEL,
    APPT_SET_LOW_INCOME_TOTAL_ROW_LABEL, NEW_LEAD_NO_APPT_TOTAL_ROW_LABEL,
    APPT_SET_MEETINGS_COMPLETED_TOTAL_ROW_LABEL,
    MM_RECRUITS_TOTAL_ROW_LABEL, MM_RECRUITS_SAMANTHA_ROW_LABEL,
    GOOGLE_SALES_TOTAL_ROW_LABEL, AI_SALES_TOTAL_ROW_LABEL,
}

DAILY_FREEZABLE_BLOCK_LABELS = {
    DAILY_CALLS_TOTAL_ROW_LABEL, DAILY_MEETINGS_TOTAL_ROW_LABEL,
    DAILY_SALES_TOTAL_ROW_LABEL,
}

# Set once by configure_freeze() at the start of main(). Any period ending
# on or after this date is re-fetched; anything ending earlier is frozen.
_FREEZE_REFRESH_FROM = None
_DAILY_REFRESH_FROM = None
_FREEZE_STATS = {"frozen": 0, "fetched": 0}


def configure_freeze(today):
    """Computes the refresh cutoff once, so every should_refetch() call in
    the run agrees on it (and so a run that straddles midnight can't change
    its mind halfway through)."""
    global _FREEZE_REFRESH_FROM, _DAILY_REFRESH_FROM
    _DAILY_REFRESH_FROM = today - timedelta(days=DAILY_REFRESH_TRAILING_DAYS)
    if not FREEZE_COMPLETED_PERIODS:
        _FREEZE_REFRESH_FROM = None
        print("Freezing is DISABLED (FREEZE_COMPLETED_PERIODS = False) - every period will be fetched live.")
        return
    _FREEZE_REFRESH_FROM = datetime(today.year, today.month, 1).date() - timedelta(days=REFRESH_TRAILING_DAYS)
    print(
        f"Freezing ENABLED: periods ending on/after {_FREEZE_REFRESH_FROM} are fetched live; "
        f"everything earlier is reused from the previous run's sheet."
    )


def should_refetch(period):
    """A period is re-fetched if freezing is off, if it's flagged live (the
    current month total, the current year YTD, the running current week), or
    if it ends on/after the refresh cutoff."""
    if not FREEZE_COMPLETED_PERIODS or _FREEZE_REFRESH_FROM is None:
        return True
    if period.live:
        return True
    if period.start_date == period.end_date and _DAILY_REFRESH_FROM is not None:
        # Single-day period (Daily tab): only the last few days refresh.
        return period.end_date >= _DAILY_REFRESH_FROM
    return period.end_date >= _FREEZE_REFRESH_FROM


def _frozen_number(value):
    """Sheet cells come back as real numbers (the read below asks for
    UNFORMATTED_VALUE), but a blank is '' and a stray text cell is possible
    - both become None so they're simply omitted from a rebuilt tally
    rather than poisoning it with a string."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


class FrozenSheet:
    """The previous run's tab, indexed so a (block, column, owner) lookup is
    O(1) and - critically - keyed by LABEL rather than position. New week
    columns and new owner rows shift everything sideways/down between runs,
    so any position-based reuse would silently write last month's number
    into this month's cell."""

    def __init__(self, header, rows, block_labels):
        self.col_index = {}
        for i, label in enumerate(header):
            label = str(label).strip() if label is not None else ""
            if label and label not in self.col_index:
                self.col_index[label] = i

        self.blocks = {}
        current = None
        for row in rows:
            raw = row[0] if row else ""
            label = str(raw).strip() if raw is not None else ""
            if label in block_labels:
                current = {"total": row, "owners": {}}
                self.blocks[label] = current
            elif not label:
                # Blank spacer row ends the current block. This is what stops
                # a derived block's Total row (Avg Sale $, Show Rate, ...)
                # from being mistaken for an owner row of the block above it.
                current = None
            elif current is not None:
                current["owners"][label] = row

    def has(self, block_label, period_label):
        return block_label in self.blocks and period_label in self.col_index

    def tally_and_total(self, block_label, period_label):
        """Rebuilds the (tally, total) pair a live fetch would have returned:
        owner rows become the tally, the block's Total row becomes the total.
        The total is read from the sheet's own Total row rather than summed
        from the owner rows, because that's how it was originally written -
        summing instead would silently change a block whose Total came from
        HubSpot's own count."""
        col = self.col_index[period_label]
        block = self.blocks[block_label]
        total_row = block["total"]
        total = _frozen_number(total_row[col]) if col < len(total_row) else None
        tally = {}
        for owner, row in block["owners"].items():
            if col >= len(row):
                continue
            value = _frozen_number(row[col])
            if value is not None:
                tally[owner] = value
        return tally, (total if total is not None else 0)


def read_frozen_sheet(spreadsheet, tab_name, block_labels):
    """Reads a tab BEFORE write_to_sheet() deletes it. Returns None if
    freezing is off or the tab doesn't exist yet (first ever run), in which
    case every period is fetched live and the run behaves exactly as it did
    before this feature existed.

    UNFORMATTED_VALUE is essential: without it the Sales $ blocks come back
    as '$12,345.00' strings rather than numbers."""
    if not FREEZE_COMPLETED_PERIODS:
        return None
    try:
        resp = sheets_retry(
            spreadsheet.values_get, f"'{tab_name}'",
            params={"valueRenderOption": "UNFORMATTED_VALUE"},
        )
    except gspread.exceptions.APIError as exc:
        print(f"  No existing '{tab_name}' tab to freeze from ({exc.__class__.__name__}) - everything will be fetched live.")
        return None
    values = resp.get("values", [])
    if len(values) < 2:
        print(f"  Existing '{tab_name}' tab is empty - everything will be fetched live.")
        return None
    frozen = FrozenSheet(values[0], values[1:], block_labels)
    print(
        f"  Read '{tab_name}': {len(frozen.blocks)} reusable block(s), "
        f"{len(frozen.col_index)} column label(s) available to freeze against."
    )
    return frozen


def freeze_fetch(fetch_fn, frozen, block_label):
    """Drop-in replacement for any (tally, total)-shaped fetch function. If
    the period is finished AND the previous run's sheet has that block and
    column, the old values are returned untouched and no HubSpot request is
    made. Otherwise it falls through to the real fetch, unchanged."""
    def wrapped(period, *args):
        if frozen is not None and not should_refetch(period) and frozen.has(block_label, period.label):
            tally, total = frozen.tally_and_total(block_label, period.label)
            _FREEZE_STATS["frozen"] += 1
            print(f"{period.label:<28} [frozen  ] reused - {len(tally)} owner buckets, {total} total")
            return tally, total
        _FREEZE_STATS["fetched"] += 1
        return fetch_fn(period, *args)
    return wrapped


def freeze_deal_fetch(fetch_fn, frozen, count_block_label, dollar_block_label=None):
    """Deals counterpart - rebuilds the 4-tuple (count_tally, dollar_tally,
    count_total, dollar_total) from the TWO sheet blocks that one deal fetch
    originally populated. Both must be present to freeze; if either is
    missing the period is fetched live, so a half-frozen deal period can't
    happen. dollar_block_label is None for the count-only blocks (Google
    Sales #, AI Sales #), whose dollar side is never written to the sheet."""
    def wrapped(period, *args):
        if (frozen is not None and not should_refetch(period)
                and frozen.has(count_block_label, period.label)
                and (dollar_block_label is None or frozen.has(dollar_block_label, period.label))):
            count_tally, count_total = frozen.tally_and_total(count_block_label, period.label)
            if dollar_block_label is None:
                dollar_tally, dollar_total = {}, 0
            else:
                dollar_tally, dollar_total = frozen.tally_and_total(dollar_block_label, period.label)
            _FREEZE_STATS["frozen"] += 1
            print(f"{period.label:<28} [frozen  ] reused - {len(count_tally)} owner buckets, {count_total} deals, ${dollar_total:,.2f}")
            return count_tally, dollar_tally, count_total, dollar_total
        _FREEZE_STATS["fetched"] += 1
        return fetch_fn(period, *args)
    return wrapped


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------

def pct_change(old_val, new_val):
    if old_val in (None, "") or new_val in (None, ""):
        return ""
    old_num, new_num = float(old_val), float(new_val)
    if old_num == 0:
        return ""
    pct = round((new_num - old_num) / old_num * 100, 1)
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct}%"


def build_metric_rows(total_row_label, period_values, period_totals, owners_seen, quick_glance_periods, grid_labels, year_total_labels):
    ly_period, cm_period, pw_period, cwr_period = quick_glance_periods

    def owner_has_data(owner):
        for label in ([ly_period.label, cm_period.label, pw_period.label, cwr_period.label] + grid_labels):
            val = period_values.get(label, {}).get(owner, "")
            if val not in ("", None, 0):
                return True
        return False

    def owner_volume(owner):
        total = 0.0
        for label in year_total_labels:
            val = period_values.get(label, {}).get(owner, "")
            if val not in ("", None):
                total += float(val)
        return total

    filled_owners = sorted((o for o in owners_seen if owner_has_data(o)), key=lambda o: (-owner_volume(o), o))
    empty_owners = sorted(o for o in owners_seen if not owner_has_data(o))
    owners_ordered = filled_owners + empty_owners

    ly_tot = period_totals.get(ly_period.label, "")
    cm_tot = period_totals.get(cm_period.label, "")
    pw_tot = period_totals.get(pw_period.label, "")
    cwr_tot = period_totals.get(cwr_period.label, "")
    total_row = [total_row_label, ly_tot, cm_tot, pct_change(ly_tot, cm_tot), pw_tot, cwr_tot, pct_change(pw_tot, cwr_tot)]
    for label in grid_labels:
        total_row.append(period_totals.get(label, ""))

    rows = [total_row]
    for owner in owners_ordered:
        ly_val = period_values.get(ly_period.label, {}).get(owner, "")
        cm_val = period_values.get(cm_period.label, {}).get(owner, "")
        pw_val = period_values.get(pw_period.label, {}).get(owner, "")
        cwr_val = period_values.get(cwr_period.label, {}).get(owner, "")
        row = [owner, ly_val, cm_val, pct_change(ly_val, cm_val), pw_val, cwr_val, pct_change(pw_val, cwr_val)]
        for label in grid_labels:
            row.append(period_values.get(label, {}).get(owner, ""))
        rows.append(row)
    return rows


def build_ratio_rows(row_label, numerator_values, denominator_values, numerator_totals, denominator_totals,
                      quick_glance_periods, grid_labels, as_percentage=False, as_currency=False, decimals=1):
    """NEW - generic derived-metric row builder: divides one already-
    fetched metric block's per-owner/per-period values by another's,
    period-by-period. Pure math on numbers already in memory - makes NO
    additional HubSpot API calls, and doesn't touch (or need) owners_seen
    from either source block. A blank or zero denominator always renders
    as a blank cell, never a divide-by-zero error. % Change columns are
    left blank for ratio rows (a % change of a ratio is a different,
    more ambiguous question than % change of a raw count - can be added
    later if useful).

    Owner rows: the union of owner keys appearing in either source block.
    CAVEAT (see module docstring point 4): when the two source blocks'
    owner keys come from different systems (free-text Leads roster names
    vs. real Owners-API names), a given owner's row may be populated on
    one side and blank on the other, producing a blank ratio cell for
    that owner even though both Total rows are independently correct."""
    ly_period, cm_period, pw_period, cwr_period = quick_glance_periods
    period_labels = [ly_period.label, cm_period.label, pw_period.label, cwr_period.label] + grid_labels

    def fmt(n, d):
        if n in (None, "") or d in (None, "", 0):
            return ""
        n, d = float(n), float(d)
        if d == 0:
            return ""
        val = n / d
        if as_percentage:
            return f"{round(val * 100, decimals)}%"
        if as_currency:
            return f"${val:,.2f}"
        return round(val, decimals)

    owners = set()
    for lbl in period_labels:
        owners.update(numerator_values.get(lbl, {}).keys())
        owners.update(denominator_values.get(lbl, {}).keys())
    owners = sorted(owners)

    def row_for(owner):
        ly = fmt(numerator_values.get(ly_period.label, {}).get(owner, ""), denominator_values.get(ly_period.label, {}).get(owner, ""))
        cm = fmt(numerator_values.get(cm_period.label, {}).get(owner, ""), denominator_values.get(cm_period.label, {}).get(owner, ""))
        pw = fmt(numerator_values.get(pw_period.label, {}).get(owner, ""), denominator_values.get(pw_period.label, {}).get(owner, ""))
        cwr = fmt(numerator_values.get(cwr_period.label, {}).get(owner, ""), denominator_values.get(cwr_period.label, {}).get(owner, ""))
        row = [owner, ly, cm, "", pw, cwr, ""]
        for label in grid_labels:
            row.append(fmt(numerator_values.get(label, {}).get(owner, ""), denominator_values.get(label, {}).get(owner, "")))
        return row

    total_row = [row_label]
    ly_t = fmt(numerator_totals.get(ly_period.label, ""), denominator_totals.get(ly_period.label, ""))
    cm_t = fmt(numerator_totals.get(cm_period.label, ""), denominator_totals.get(cm_period.label, ""))
    pw_t = fmt(numerator_totals.get(pw_period.label, ""), denominator_totals.get(pw_period.label, ""))
    cwr_t = fmt(numerator_totals.get(cwr_period.label, ""), denominator_totals.get(cwr_period.label, ""))
    total_row += [ly_t, cm_t, "", pw_t, cwr_t, ""]
    for label in grid_labels:
        total_row.append(fmt(numerator_totals.get(label, ""), denominator_totals.get(label, "")))

    rows = [total_row]
    for owner in owners:
        rows.append(row_for(owner))
    return rows


def build_total_only_rows(total_row_label, period_totals, quick_glance_periods, grid_labels):
    """NEW - same Total-row construction as the first row of
    build_metric_rows, but WITHOUT any owner rows underneath - used for
    metrics that are explicitly total-only per your instructions (AI/
    ChatGPT Leads, MM Recruits, MM Recruits - Samantha). Returns a
    single-row list, same [row_label, ...] shape as every other block's
    total row, so it drops straight into the same data_rows assembly."""
    ly_period, cm_period, pw_period, cwr_period = quick_glance_periods
    ly_tot = period_totals.get(ly_period.label, "")
    cm_tot = period_totals.get(cm_period.label, "")
    pw_tot = period_totals.get(pw_period.label, "")
    cwr_tot = period_totals.get(cwr_period.label, "")
    row = [total_row_label, ly_tot, cm_tot, pct_change(ly_tot, cm_tot), pw_tot, cwr_tot, pct_change(pw_tot, cwr_tot)]
    for label in grid_labels:
        row.append(period_totals.get(label, ""))
    return [row]


def build_sum_rows(row_label, totals_list, quick_glance_periods, grid_labels):
    """NEW - Total Organic Leads Assigned = Total Google Leads Assigned +
    Total AI/ChatGPT Leads Assigned, period-by-period. Pure addition on
    totals already fetched by those two blocks - makes NO additional
    HubSpot API calls. Total-only (no owner rows), same reasoning as
    build_total_only_rows: AI Leads has no owner breakdown to sum against,
    so a per-owner Organic row isn't meaningful here."""
    ly_period, cm_period, pw_period, cwr_period = quick_glance_periods

    def s(label):
        return sum(float(totals.get(label, 0) or 0) for totals in totals_list)

    ly, cm, pw, cwr = s(ly_period.label), s(cm_period.label), s(pw_period.label), s(cwr_period.label)
    row = [row_label, ly, cm, pct_change(ly, cm), pw, cwr, pct_change(pw, cwr)]
    for label in grid_labels:
        row.append(s(label))
    return [row]


def build_daily_metric_rows(total_row_label, period_values, period_totals, owners_seen, daily_columns):
    """NEW - Daily-tab counterpart to build_metric_rows: one column per
    daily_columns entry (a real day Period, or None for a between-week
    spacer, which always renders as a blank cell), no quick-glance/week/
    month/year columns. Owners are ordered by total volume across all
    real (non-spacer) days, highest first, same tie-breaking (owners with
    zero everywhere sort after, then alphabetically) as build_metric_rows."""
    def owner_has_data(owner):
        for col in daily_columns:
            if col is None:
                continue
            val = period_values.get(col.label, {}).get(owner, "")
            if val not in ("", None, 0):
                return True
        return False

    def owner_volume(owner):
        total = 0.0
        for col in daily_columns:
            if col is None:
                continue
            val = period_values.get(col.label, {}).get(owner, "")
            if val not in ("", None):
                total += float(val)
        return total

    filled_owners = sorted((o for o in owners_seen if owner_has_data(o)), key=lambda o: (-owner_volume(o), o))
    empty_owners = sorted(o for o in owners_seen if not owner_has_data(o))
    owners_ordered = filled_owners + empty_owners

    def row_values(lookup):
        return [("" if col is None else lookup(col.label)) for col in daily_columns]

    total_row = [total_row_label] + row_values(lambda label: period_totals.get(label, ""))
    rows = [total_row]
    for owner in owners_ordered:
        rows.append([owner] + row_values(lambda label, o=owner: period_values.get(label, {}).get(o, "")))
    return rows


def build_daily_blank_rows(total_row_label, owners, daily_columns):
    """NEW - Hours block for the Daily tab: Total row + one row per owner
    (the union of owners seen in the Calls/Meetings/Sales blocks, so the
    roster lines up across all four blocks), every cell blank (spacer
    columns included). No HubSpot property for hours worked was given, so
    this is left empty rather than guessed at - fill in later once you
    tell me the source."""
    rows = [[total_row_label] + [""] * len(daily_columns)]
    for owner in sorted(owners):
        rows.append([owner] + [""] * len(daily_columns))
    return rows


# ---------------------------------------------------------------------------
# Google Sheets read/write
# ---------------------------------------------------------------------------

def sheets_retry(fn, *args, max_retries=5, **kwargs):
    """NEW - retries a gspread/Sheets API call on transient errors (429,
    5xx) the same way request_with_retry() above does for HubSpot calls.
    gspread wraps any non-2xx response in a gspread.exceptions.APIError,
    so this checks THAT exception's underlying HTTP status the way
    request_with_retry checks requests.Response.status_code directly.

    Added after a run hit a bare 503 from Google's Sheets API on the very
    FIRST Sheets call (client.open_by_key), which happened after ~20-30
    minutes of successful HubSpot fetching - since no Sheets call had any
    retry logic, that one transient blip killed the entire run at the
    last step, discarding all the already-fetched data. Every gspread
    call below is now routed through this wrapper for the same reason
    HubSpot calls go through request_with_retry: a transient error on
    Google's end shouldn't cost 20+ minutes of re-fetching."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as exc:
            status = None
            try:
                status = exc.response.status_code
            except AttributeError:
                pass
            if status is not None and (status == 429 or status >= 500):
                wait = 2 ** attempt
                print(f"  Sheets API error ({status}) - waiting {wait}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(wait)
                last_exc = exc
                continue
            raise
    raise last_exc


def _sheets_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=scopes)
    return gspread.authorize(creds)


def open_spreadsheet():
    """NEW (round 7) - opening moved OUT of write_to_sheet so main() can do
    it FIRST: the previous run's values have to be read before that tab is
    deleted, and doing it up front also means a credentials/sharing problem
    surfaces in the first second rather than after a long fetch."""
    client = _sheets_client()
    try:
        return sheets_retry(client.open_by_key, SPREADSHEET_ID)
    except gspread.exceptions.APIError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (403, 404):
            sa = SERVICE_ACCOUNT_INFO.get("client_email", "(unknown)")
            sys.exit(
                f"ERROR: cannot open the spreadsheet ({status}).\n"
                f"  https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit\n"
                f"Share it with EDIT access to:\n  {sa}"
            )
        raise


def write_to_sheet(spreadsheet, header_row, data_rows):
    """CHANGED (round 7): takes the already-open spreadsheet instead of
    opening its own, so the freeze read in main() happens against the same
    handle - and, more importantly, BEFORE this function deletes the tab."""
    try:
        old_worksheet = sheets_retry(spreadsheet.worksheet, SHEET_TAB_NAME)
        sheets_retry(spreadsheet.del_worksheet, old_worksheet)
    except gspread.exceptions.WorksheetNotFound:
        pass

    worksheet = sheets_retry(spreadsheet.add_worksheet, title=SHEET_TAB_NAME, rows=len(data_rows) + 10, cols=len(header_row) + 5)

    sheets_retry(worksheet.update, values=[header_row] + data_rows, range_name="A1")
    print(f"\nWrote {len(data_rows)} rows x {len(header_row) - 1} period columns to '{SHEET_TAB_NAME}'.")
    return worksheet


def apply_column_groups(spreadsheet, worksheet, quick_glance_labels, year_blocks):
    """UNCHANGED - column groups don't care how many row-blocks are
    stacked underneath them."""
    sheet_id = worksheet.id
    requests_batch = []
    week_group_ranges = []

    col = 1

    qg_start = col
    col += len(quick_glance_labels)
    qg_end = col
    requests_batch.append({"addDimensionGroup": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": qg_start, "endIndex": qg_end}}})

    for yb in year_blocks:
        year_start = col
        for month in yb["months"]:
            month_start = col
            col += len(month["weeks"])
            month_weeks_end = col
            if month["weeks"]:
                requests_batch.append({"addDimensionGroup": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": month_start, "endIndex": month_weeks_end}}})
                week_group_ranges.append({"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": month_start, "endIndex": month_weeks_end})
            col += 1
        year_months_end = col
        requests_batch.append({"addDimensionGroup": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": year_start, "endIndex": year_months_end}}})
        col += 1

    sheets_retry(spreadsheet.batch_update, {"requests": requests_batch})
    print(f"Applied {len(requests_batch)} column groups (quick-glance + {len(year_blocks)} year groups + nested month groups).")

    collapse_requests = []
    for rng in week_group_ranges:
        collapse_requests.append({"updateDimensionGroup": {"dimensionGroup": {"range": rng, "depth": 2, "collapsed": True}, "fields": "collapsed"}})
        collapse_requests.append({"updateDimensionProperties": {"range": rng, "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
    if collapse_requests:
        sheets_retry(spreadsheet.batch_update, {"requests": collapse_requests})
        print(f"Collapsed {len(week_group_ranges)} weekly groups - sheet now defaults to year/month view.")


def apply_row_groups(spreadsheet, worksheet, owner_row_ranges):
    """NEW - collapses each metric block's per-owner rows underneath its
    Total row, using Sheets ROW dimension groups (the same primitive
    already used for the weekly COLUMN groups in apply_column_groups,
    just on the other axis). Collapsed by default, so the sheet opens
    showing just the bold Total rows - each gets a '+' expand control
    in the row-number gutter on the left to reveal that block's full
    owner breakdown, mirroring the existing weekly/monthly column-
    collapse UX. owner_row_ranges is a list of (start_row, end_row)
    0-based, end-exclusive row index pairs - one per metric block,
    covering that block's owner rows only (never the Total row itself,
    so the Total row always stays visible even when collapsed)."""
    sheet_id = worksheet.id

    group_requests = [
        {"addDimensionGroup": {"range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": start_row, "endIndex": end_row}}}
        for start_row, end_row in owner_row_ranges if end_row > start_row
    ]
    if group_requests:
        sheets_retry(spreadsheet.batch_update, {"requests": group_requests})

    collapse_requests = []
    for start_row, end_row in owner_row_ranges:
        if end_row <= start_row:
            continue
        rng = {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": start_row, "endIndex": end_row}
        collapse_requests.append({"updateDimensionGroup": {"dimensionGroup": {"range": rng, "depth": 1, "collapsed": True}, "fields": "collapsed"}})
        collapse_requests.append({"updateDimensionProperties": {"range": rng, "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
    if collapse_requests:
        sheets_retry(spreadsheet.batch_update, {"requests": collapse_requests})

    print(f"Applied {len(group_requests)} row groups (owner-level detail collapsed under each metric's Total row).")


def apply_formatting(spreadsheet, worksheet, num_quick_glance_cols, year_blocks, total_row_indices, spacer_row_indices=None, currency_row_ranges=None):
    """Same formatting as before, generalized to accept a LIST of total-row
    indices and an optional list of spacer-row indices. UNCHANGED apart
    from that generalization - no new parameters added, since the new
    ratio blocks bake their $/% formatting directly into the cell string
    values (via build_ratio_rows' fmt()) rather than needing a Sheets-
    level numberFormat override."""
    sheet_id = worksheet.id
    row_count = worksheet.row_count
    col_count = worksheet.col_count
    requests_batch = []

    requests_batch.append({
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 1}},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    })

    requests_batch.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": col_count},
            "cell": {"userEnteredFormat": {
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "backgroundColor": {"red": 0.20, "green": 0.26, "blue": 0.33},
                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP",
            }},
            "fields": "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy)",
        }
    })

    requests_batch.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count, "startColumnIndex": 1, "endColumnIndex": col_count},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    })

    requests_batch.append({
        "addBanding": {
            "bandedRange": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": row_count, "startColumnIndex": 0, "endColumnIndex": col_count},
                "rowProperties": {
                    "headerColor": {"red": 0.20, "green": 0.26, "blue": 0.33},
                    "firstBandColor": {"red": 1, "green": 1, "blue": 1},
                    "secondBandColor": {"red": 0.95, "green": 0.95, "blue": 0.96},
                },
            }
        }
    })

    requests_batch.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 150}, "fields": "pixelSize"}})
    requests_batch.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 1 + num_quick_glance_cols}, "properties": {"pixelSize": 105}, "fields": "pixelSize"}})

    col = 1 + num_quick_glance_cols
    for yb in year_blocks:
        for month in yb["months"]:
            week_count = len(month["weeks"])
            if week_count:
                requests_batch.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": col, "endIndex": col + week_count}, "properties": {"pixelSize": 55}, "fields": "pixelSize"}})
            col += week_count
            requests_batch.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": col, "endIndex": col + 1}, "properties": {"pixelSize": 90}, "fields": "pixelSize"}})
            requests_batch.append({
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count, "startColumnIndex": col, "endColumnIndex": col + 1},
                    "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.90, "green": 0.93, "blue": 0.98}, "textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat(backgroundColor,textFormat.bold)",
                }
            })
            col += 1
        requests_batch.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": col, "endIndex": col + 1}, "properties": {"pixelSize": 100}, "fields": "pixelSize"}})
        requests_batch.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count, "startColumnIndex": col, "endColumnIndex": col + 1},
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.80, "green": 0.87, "blue": 0.98}, "textFormat": {"bold": True}}},
                "fields": "userEnteredFormat(backgroundColor,textFormat.bold)",
            }
        })
        col += 1

    pct_yoy_col = 1 + 2
    pct_wow_col = 1 + 5
    for pct_col in (pct_yoy_col, pct_wow_col):
        requests_batch.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count, "startColumnIndex": pct_col, "endColumnIndex": pct_col + 1},
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.80}, "textFormat": {"italic": True}, "horizontalAlignment": "CENTER"}},
                "fields": "userEnteredFormat(backgroundColor,textFormat.italic,horizontalAlignment)",
            }
        })
        requests_batch.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count, "startColumnIndex": pct_col, "endColumnIndex": pct_col + 1}],
                    "booleanRule": {"condition": {"type": "TEXT_STARTS_WITH", "values": [{"userEnteredValue": "+"}]}, "format": {"textFormat": {"foregroundColor": {"red": 0.0, "green": 0.5, "blue": 0.0}, "bold": True}}},
                },
                "index": 0,
            }
        })
        requests_batch.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count, "startColumnIndex": pct_col, "endColumnIndex": pct_col + 1}],
                    "booleanRule": {"condition": {"type": "TEXT_STARTS_WITH", "values": [{"userEnteredValue": "-"}]}, "format": {"textFormat": {"foregroundColor": {"red": 0.80, "green": 0.0, "blue": 0.0}, "bold": True}}},
                },
                "index": 0,
            }
        })

    for row_idx in total_row_indices:
        requests_batch.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": col_count},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "underline": True}, "backgroundColor": {"red": 1.0, "green": 0.93, "blue": 0.70}}},
                "fields": "userEnteredFormat(textFormat.bold,textFormat.underline,backgroundColor)",
            }
        })

    for row_idx in (spacer_row_indices or []):
        requests_batch.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": col_count},
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85}}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        })

    for start_row, end_row in (currency_row_ranges or []):
        requests_batch.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row, "endRowIndex": end_row, "startColumnIndex": 1, "endColumnIndex": col_count},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "CURRENCY", "pattern": "$#,##0.00"}}},
                "fields": "userEnteredFormat.numberFormat",
            }
        })

    sheets_retry(spreadsheet.batch_update, {"requests": requests_batch})
    print(f"Applied {len(requests_batch)} formatting requests (freeze panes, header styling, number format, banding, column widths, {len(total_row_indices)} total-row(s), {len(spacer_row_indices or [])} spacer row(s)).")


def write_daily_tab(spreadsheet, header_row, data_rows):
    """NEW - writes the Daily tab to the SAME spreadsheet the Master
    Metric Sheet tab lives in (spreadsheet is the object returned by
    write_to_sheet, so this doesn't re-open the file). Replaces any
    existing 'Daily' worksheet, same pattern as write_to_sheet."""
    try:
        old_worksheet = sheets_retry(spreadsheet.worksheet, DAILY_SHEET_TAB_NAME)
        sheets_retry(spreadsheet.del_worksheet, old_worksheet)
    except gspread.exceptions.WorksheetNotFound:
        pass

    worksheet = sheets_retry(spreadsheet.add_worksheet, title=DAILY_SHEET_TAB_NAME, rows=len(data_rows) + 10, cols=len(header_row) + 5)
    sheets_retry(worksheet.update, values=[header_row] + data_rows, range_name="A1")
    print(f"\nWrote {len(data_rows)} rows x {len(header_row) - 1} day columns to '{DAILY_SHEET_TAB_NAME}'.")
    return worksheet


def apply_daily_formatting(spreadsheet, worksheet, total_row_indices, spacer_row_indices):
    """NEW - lightweight formatting for the Daily tab: freeze header
    row/first column, bold header, number formatting, banding, and bold
    highlighted Total rows + grey spacer rows - the same visual language
    as apply_formatting above, without the weekly/monthly column-width and
    quick-glance-specific logic (the Daily tab has no such columns)."""
    sheet_id = worksheet.id
    row_count = worksheet.row_count
    col_count = worksheet.col_count
    requests_batch = []

    requests_batch.append({
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 1}},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    })
    requests_batch.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": col_count},
            "cell": {"userEnteredFormat": {
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "backgroundColor": {"red": 0.20, "green": 0.26, "blue": 0.33},
                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP",
            }},
            "fields": "userEnteredFormat(textFormat,backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy)",
        }
    })
    requests_batch.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": row_count, "startColumnIndex": 1, "endColumnIndex": col_count},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    })
    requests_batch.append({
        "addBanding": {
            "bandedRange": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": row_count, "startColumnIndex": 0, "endColumnIndex": col_count},
                "rowProperties": {
                    "headerColor": {"red": 0.20, "green": 0.26, "blue": 0.33},
                    "firstBandColor": {"red": 1, "green": 1, "blue": 1},
                    "secondBandColor": {"red": 0.95, "green": 0.95, "blue": 0.96},
                },
            }
        }
    })
    requests_batch.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 150}, "fields": "pixelSize"}})
    requests_batch.append({"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": col_count}, "properties": {"pixelSize": 70}, "fields": "pixelSize"}})

    for row_idx in total_row_indices:
        requests_batch.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": col_count},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "underline": True}, "backgroundColor": {"red": 1.0, "green": 0.93, "blue": 0.70}}},
                "fields": "userEnteredFormat(textFormat.bold,textFormat.underline,backgroundColor)",
            }
        })
    for row_idx in spacer_row_indices:
        requests_batch.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 0, "endColumnIndex": col_count},
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85}}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        })

    sheets_retry(spreadsheet.batch_update, {"requests": requests_batch})
    print(f"Applied {len(requests_batch)} formatting requests to '{DAILY_SHEET_TAB_NAME}' (freeze panes, header styling, banding, {len(total_row_indices)} total-row(s)).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    token = get_access_token()
    today = local_today()

    # --- NEW (round 7): freeze setup, FIRST, before anything is fetched ---
    # The previous run's values must be read before write_to_sheet() deletes
    # those tabs. Opening the spreadsheet here also fails fast on a
    # credentials/sharing problem instead of after a long fetch.
    configure_freeze(today)
    spreadsheet = open_spreadsheet()
    print(f"Opened '{spreadsheet.title}'.")
    frozen_master = read_frozen_sheet(spreadsheet, SHEET_TAB_NAME, MASTER_FREEZABLE_BLOCK_LABELS)
    frozen_daily = read_frozen_sheet(spreadsheet, DAILY_SHEET_TAB_NAME, DAILY_FREEZABLE_BLOCK_LABELS)
    print()

    # --- Leads Assigned: property/roster resolution (UNCHANGED) ---
    filter_property = resolve_property(token, OWNER_FILTER_PROPERTY_LABEL_KEYWORDS, "filter")
    display_property = resolve_property(token, OWNER_DISPLAY_PROPERTY_LABEL_KEYWORDS, "display")
    leads_owner_roster = build_roster_from_recent_window(token, filter_property, display_property, today)

    # --- Meetings Completed: property resolution (UNCHANGED) ---
    meetings_date_property = resolve_activity_date_property(token, "meetings")
    meetings_owner_property = resolve_owner_property_for_object(token, "meetings")
    meetings_outcome_property, meetings_outcome_value = resolve_meeting_outcome_completed_value(token)
    meetings_extra_filters = [{"propertyName": meetings_outcome_property, "operator": "IN", "values": [meetings_outcome_value]}]

    # --- Calls: property resolution (UNCHANGED) ---
    calls_date_property = resolve_activity_date_property(token, "calls")
    calls_owner_property = resolve_owner_property_for_object(token, "calls")

    # --- Sales # / Sales $: property + pipeline/stage resolution (UNCHANGED) ---
    closed_won_date_property = resolve_closed_won_date_property(token)
    deal_owner_property = resolve_deal_owner_property(token)
    deal_amount_property = resolve_amount_property(token)
    closed_won_dealstage_values = resolve_closed_won_dealstages(token)

    # --- NEW: New Business / Renewals - single-stage resolution ---
    new_business_stage_id = resolve_deal_stage_by_exact_label(token, NEW_BUSINESS_STAGE_EXACT_LABEL)
    renewal_stage_id = resolve_deal_stage_by_exact_label(token, RENEWAL_STAGE_EXACT_LABEL)

    # --- NEW: Sales from Old Leads (60+ Days) - dropdown value resolution ---
    old_lead_yes_value = resolve_old_lead_yes_value(token)
    old_lead_extra_filters = [{"propertyName": OLD_LEAD_PROPERTY, "operator": "EQ", "value": old_lead_yes_value}]

    # --- Shared active-owner roster for Meetings + Calls + Deals blocks (UNCHANGED) ---
    owners_map = fetch_active_owners(token)

    # --- NEW (round 2/4): Google Leads / AI Leads property resolution ---
    source_property = resolve_contact_property_exact_label(token, SOURCE_PROPERTY_EXACT_LABEL, "source", fallback_keywords=["source"])
    inferred_landing_page_property = resolve_contact_property_exact_label(
        token, INFERRED_LANDING_PAGE_EXACT_LABEL, "inferred landing page", fallback_keywords=["inferred landing page"]
    )

    # --- NEW (round 5, FIXED round 6): Google Sales / AI Sales - deal-level
    # source property resolution.
    #
    # "Source*" is a CONTACT label only; on the deal object this portal's
    # equivalent is "Deal Source " (deal_source), so it's supplied via
    # DEAL_SOURCE_PROPERTY_OVERRIDE rather than looked up by label - see
    # the config block for the full explanation (a substring match on
    # "source" hit 25 candidates and correctly refused to guess).
    if DEAL_SOURCE_PROPERTY_OVERRIDE:
        deal_source_property = verify_deal_property_exists(token, DEAL_SOURCE_PROPERTY_OVERRIDE, "deal source")
    else:
        deal_source_property = resolve_deal_property_exact_label(
            token, DEAL_SOURCE_PROPERTY_EXACT_LABEL, "deal source", fallback_keywords=DEAL_SOURCE_FALLBACK_KEYWORDS
        )

    # The deal-level Inferred Landing Page is OPTIONAL, and CONFIRMED ABSENT
    # on your portal (see the config note) - so by default the lookup is
    # skipped outright and Block 28 below drops its second OR-branch. If the
    # lookup is re-enabled it stays non-fatal: a failure warns and returns
    # None rather than killing the run.
    if not DEAL_INFERRED_LANDING_PAGE_LOOKUP_ENABLED and not DEAL_INFERRED_LANDING_PAGE_PROPERTY_OVERRIDE:
        deal_inferred_landing_page_property = None
        print(
            "Skipping deal-level 'Inferred Landing Page' lookup - CONFIRMED not to exist on the deal object in this "
            "portal (DEAL_INFERRED_LANDING_PAGE_LOOKUP_ENABLED is False). AI Sales # will run single-branch; see the "
            "config note for the under-count consequence."
        )
    elif DEAL_INFERRED_LANDING_PAGE_PROPERTY_OVERRIDE:
        deal_inferred_landing_page_property = verify_deal_property_exists(
            token, DEAL_INFERRED_LANDING_PAGE_PROPERTY_OVERRIDE, "deal inferred landing page"
        )
    else:
        deal_inferred_landing_page_property = resolve_deal_property_optional(
            token, INFERRED_LANDING_PAGE_EXACT_LABEL, "deal inferred landing page",
            fallback_keywords=DEAL_INFERRED_LANDING_PAGE_FALLBACK_KEYWORDS,
        )

    # --- NEW (round 2): Appt Set family property resolution ---
    appt_set_calc_property = resolve_contact_property_exact_label(token, APPOINTMENT_SET_CALC_EXACT_LABEL, "appointment set calculation", fallback_keywords=["appointment set calculation"])
    date_met_with_property = resolve_contact_property_exact_label(token, DATE_MET_WITH_EXACT_LABEL, "date met with", fallback_keywords=["date met with"])
    income_property = INCOME_PROPERTY_OVERRIDE or resolve_contact_property_exact_label(token, INCOME_PROPERTY_EXACT_LABEL, "income", fallback_keywords=["income"])
    if INCOME_PROPERTY_OVERRIDE:
        print(f"Using manual income property override: '{INCOME_PROPERTY_OVERRIDE}' (auto-resolution skipped).")
    verify_income_property_type(token, income_property, INCOME_LOW_VALUES + INCOME_HIGH_VALUES)

    # --- NEW (round 2): classic list membership (client-side exclusion) ---
    appt_set_exclude_ids = fetch_list_membership_ids(token, APPT_SET_EXCLUDE_LIST_ID)
    imported_list_id = resolve_list_id_by_name_keywords(token, NEW_LEAD_NO_APPT_EXCLUDE_LIST_NAME_KEYWORDS, "New Lead (no appt) / Appt Set Meetings Completed exclusion")
    imported_list_exclude_ids = fetch_list_membership_ids(token, imported_list_id)

    # --- Shared period tree / columns (built ONCE, used by every block) ---
    quick_glance, year_blocks = build_period_tree(today)
    year_blocks_desc = list(reversed(year_blocks))
    all_periods = flatten_periods([], year_blocks_desc)
    grid_labels = [p.label for p in all_periods]
    year_total_labels = [yb["year_total"].label for yb in year_blocks]

    quick_glance_labels = [
        quick_glance[0].label, quick_glance[1].label, "% Change (YoY Month)",
        quick_glance[2].label, quick_glance[3].label, "% Change (WoW)",
    ]
    header_row = ["Owner"] + quick_glance_labels + grid_labels

    # Shared thread pool for every block's concurrent week-fetching.
    with ThreadPoolExecutor(max_workers=WEEK_FETCH_CONCURRENCY) as executor:

        # --------------------------------------------------------------
        # Block 1: Leads Assigned (UNCHANGED)
        # --------------------------------------------------------------
        leads_period_values, leads_period_totals, leads_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_period_live, frozen_master, TOTAL_ROW_LABEL), (token, filter_property, display_property, leads_owner_roster),
        )
        leads_rows = build_metric_rows(TOTAL_ROW_LABEL, leads_period_values, leads_period_totals, leads_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 2: Meetings Completed (UNCHANGED)
        # --------------------------------------------------------------
        meetings_period_values, meetings_period_totals, meetings_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_period_live_engagement, frozen_master, MEETINGS_TOTAL_ROW_LABEL), (token, "meetings", meetings_date_property, meetings_owner_property, owners_map, meetings_extra_filters, MEETINGS_TIMEZONE),
        )
        meetings_rows = build_metric_rows(MEETINGS_TOTAL_ROW_LABEL, meetings_period_values, meetings_period_totals, meetings_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 3: Calls (UNCHANGED)
        # --------------------------------------------------------------
        calls_period_values, calls_period_totals, calls_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_period_live_engagement, frozen_master, CALLS_TOTAL_ROW_LABEL), (token, "calls", calls_date_property, calls_owner_property, owners_map, None, CALLS_TIMEZONE),
        )
        calls_rows = build_metric_rows(CALLS_TOTAL_ROW_LABEL, calls_period_values, calls_period_totals, calls_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Blocks 4 & 5: Sales # and Sales $ (UNCHANGED)
        # --------------------------------------------------------------
        sales_count_values, sales_count_totals, sales_dollar_values, sales_dollar_totals, sales_owners_seen = fetch_deal_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_deal_fetch(fetch_deal_period_live, frozen_master, SALES_COUNT_TOTAL_ROW_LABEL, SALES_DOLLAR_TOTAL_ROW_LABEL), (token, closed_won_date_property, DEALSTAGE_PROPERTY, closed_won_dealstage_values, deal_amount_property, deal_owner_property, owners_map, SALES_TIMEZONE),
        )
        sales_count_rows = build_metric_rows(SALES_COUNT_TOTAL_ROW_LABEL, sales_count_values, sales_count_totals, sales_owners_seen, quick_glance, grid_labels, year_total_labels)
        sales_dollar_rows = build_metric_rows(SALES_DOLLAR_TOTAL_ROW_LABEL, sales_dollar_values, sales_dollar_totals, sales_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Blocks 6 & 7: New Business #/$ (NEW - dealstage = "Closed won" ONLY)
        # --------------------------------------------------------------
        nb_count_values, nb_count_totals, nb_dollar_values, nb_dollar_totals, nb_owners_seen = fetch_deal_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_deal_fetch(fetch_deal_period_live, frozen_master, NEW_BUSINESS_COUNT_TOTAL_ROW_LABEL, NEW_BUSINESS_DOLLAR_TOTAL_ROW_LABEL), (token, closed_won_date_property, DEALSTAGE_PROPERTY, [new_business_stage_id], deal_amount_property, deal_owner_property, owners_map, SALES_TIMEZONE),
        )
        new_business_count_rows = build_metric_rows(NEW_BUSINESS_COUNT_TOTAL_ROW_LABEL, nb_count_values, nb_count_totals, nb_owners_seen, quick_glance, grid_labels, year_total_labels)
        new_business_dollar_rows = build_metric_rows(NEW_BUSINESS_DOLLAR_TOTAL_ROW_LABEL, nb_dollar_values, nb_dollar_totals, nb_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Blocks 8 & 9: Renewals #/$ (NEW - dealstage = "Renewal - Closed won" ONLY)
        # --------------------------------------------------------------
        ren_count_values, ren_count_totals, ren_dollar_values, ren_dollar_totals, ren_owners_seen = fetch_deal_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_deal_fetch(fetch_deal_period_live, frozen_master, RENEWALS_COUNT_TOTAL_ROW_LABEL, RENEWALS_DOLLAR_TOTAL_ROW_LABEL), (token, closed_won_date_property, DEALSTAGE_PROPERTY, [renewal_stage_id], deal_amount_property, deal_owner_property, owners_map, SALES_TIMEZONE),
        )
        renewals_count_rows = build_metric_rows(RENEWALS_COUNT_TOTAL_ROW_LABEL, ren_count_values, ren_count_totals, ren_owners_seen, quick_glance, grid_labels, year_total_labels)
        renewals_dollar_rows = build_metric_rows(RENEWALS_DOLLAR_TOTAL_ROW_LABEL, ren_dollar_values, ren_dollar_totals, ren_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Blocks 10 & 11: Sales from Old Leads (60+ Days) #/$ (NEW)
        # --------------------------------------------------------------
        ol_count_values, ol_count_totals, ol_dollar_values, ol_dollar_totals, ol_owners_seen = fetch_deal_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_deal_fetch(fetch_deal_period_live, frozen_master, OLD_LEAD_SALES_COUNT_TOTAL_ROW_LABEL, OLD_LEAD_SALES_DOLLAR_TOTAL_ROW_LABEL), (token, closed_won_date_property, DEALSTAGE_PROPERTY, closed_won_dealstage_values, deal_amount_property, deal_owner_property, owners_map, SALES_TIMEZONE, old_lead_extra_filters),
        )
        old_lead_count_rows = build_metric_rows(OLD_LEAD_SALES_COUNT_TOTAL_ROW_LABEL, ol_count_values, ol_count_totals, ol_owners_seen, quick_glance, grid_labels, year_total_labels)
        old_lead_dollar_rows = build_metric_rows(OLD_LEAD_SALES_DOLLAR_TOTAL_ROW_LABEL, ol_dollar_values, ol_dollar_totals, ol_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 16: Google Leads Assigned (NEW - owner level)
        # --------------------------------------------------------------
        google_leads_builder = partial(build_google_leads_branches, source_property)
        google_leads_values, google_leads_totals, google_leads_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, GOOGLE_LEADS_TOTAL_ROW_LABEL), (token, google_leads_builder, display_property, leads_owner_roster, None),
        )
        google_leads_rows = build_metric_rows(GOOGLE_LEADS_TOTAL_ROW_LABEL, google_leads_values, google_leads_totals, google_leads_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 17: AI/ChatGPT Leads (NEW - total only)
        # --------------------------------------------------------------
        ai_leads_builder = partial(build_ai_leads_branches, source_property, inferred_landing_page_property)
        _ai_leads_values, ai_leads_totals, _ai_leads_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, AI_LEADS_TOTAL_ROW_LABEL), (token, ai_leads_builder, display_property, leads_owner_roster, None),
        )
        ai_leads_rows = build_total_only_rows(AI_LEADS_TOTAL_ROW_LABEL, ai_leads_totals, quick_glance, grid_labels)

        # --------------------------------------------------------------
        # Block 18: Appt Set (NEW - owner level, excludes list 1090)
        # --------------------------------------------------------------
        appt_set_builder = partial(build_appt_set_branches, appt_set_calc_property)
        appt_set_values, appt_set_totals, appt_set_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, APPT_SET_TOTAL_ROW_LABEL), (token, appt_set_builder, display_property, leads_owner_roster, appt_set_exclude_ids),
        )
        appt_set_rows = build_metric_rows(APPT_SET_TOTAL_ROW_LABEL, appt_set_values, appt_set_totals, appt_set_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 19: Appt Set High Income (75k+) (NEW - owner level)
        # --------------------------------------------------------------
        appt_set_high_income_builder = partial(build_appt_set_high_income_branches, appt_set_calc_property, income_property)
        high_income_values, high_income_totals, high_income_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, APPT_SET_HIGH_INCOME_TOTAL_ROW_LABEL), (token, appt_set_high_income_builder, display_property, leads_owner_roster, appt_set_exclude_ids),
        )
        appt_set_high_income_rows = build_metric_rows(APPT_SET_HIGH_INCOME_TOTAL_ROW_LABEL, high_income_values, high_income_totals, high_income_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 20: Appt Set Low Income (0-75k) (NEW - owner level)
        # --------------------------------------------------------------
        appt_set_low_income_builder = partial(build_appt_set_low_income_branches, appt_set_calc_property, income_property)
        low_income_values, low_income_totals, low_income_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, APPT_SET_LOW_INCOME_TOTAL_ROW_LABEL), (token, appt_set_low_income_builder, display_property, leads_owner_roster, appt_set_exclude_ids),
        )
        appt_set_low_income_rows = build_metric_rows(APPT_SET_LOW_INCOME_TOTAL_ROW_LABEL, low_income_values, low_income_totals, low_income_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 21: New Lead (no appt) (NEW - owner level, excludes "imported")
        # CONFIRMED (round 4, FIX F) - Appointment Set Calculation NEQ '1'.
        # --------------------------------------------------------------
        new_lead_no_appt_builder = partial(build_new_lead_no_appt_branches, appt_set_calc_property)
        new_lead_no_appt_values, new_lead_no_appt_totals, new_lead_no_appt_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, NEW_LEAD_NO_APPT_TOTAL_ROW_LABEL), (token, new_lead_no_appt_builder, display_property, leads_owner_roster, imported_list_exclude_ids),
        )
        new_lead_no_appt_rows = build_metric_rows(NEW_LEAD_NO_APPT_TOTAL_ROW_LABEL, new_lead_no_appt_values, new_lead_no_appt_totals, new_lead_no_appt_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 22: Appt Set Meetings Completed (NEW - owner level, excludes "imported")
        # --------------------------------------------------------------
        appt_set_meetings_completed_builder = partial(build_appt_set_meetings_completed_branches, appt_set_calc_property, date_met_with_property)
        meetings_completed_values, meetings_completed_totals, meetings_completed_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, APPT_SET_MEETINGS_COMPLETED_TOTAL_ROW_LABEL), (token, appt_set_meetings_completed_builder, display_property, leads_owner_roster, imported_list_exclude_ids),
        )
        appt_set_meetings_completed_rows = build_metric_rows(APPT_SET_MEETINGS_COMPLETED_TOTAL_ROW_LABEL, meetings_completed_values, meetings_completed_totals, meetings_completed_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 23: MM Recruits (NEW - total only; FLAG: same filter as
        # Total Leads Assigned - see MM_RECRUITS_TOTAL_ROW_LABEL comment)
        # --------------------------------------------------------------
        mm_recruits_builder = partial(build_mm_recruits_branches, filter_property)
        _mm_recruits_values, mm_recruits_totals, _mm_recruits_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, MM_RECRUITS_TOTAL_ROW_LABEL), (token, mm_recruits_builder, display_property, leads_owner_roster, None),
        )
        mm_recruits_rows = build_total_only_rows(MM_RECRUITS_TOTAL_ROW_LABEL, mm_recruits_totals, quick_glance, grid_labels)

        # --------------------------------------------------------------
        # Block 24: MM Recruits - Samantha (NEW - total only)
        # --------------------------------------------------------------
        mm_recruits_samantha_builder = partial(build_mm_recruits_samantha_branches, filter_property, display_property)
        _mm_samantha_values, mm_samantha_totals, _mm_samantha_owners_seen = fetch_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_fetch(fetch_new_contact_metric_period_live, frozen_master, MM_RECRUITS_SAMANTHA_ROW_LABEL), (token, mm_recruits_samantha_builder, display_property, leads_owner_roster, None),
        )
        mm_recruits_samantha_rows = build_total_only_rows(MM_RECRUITS_SAMANTHA_ROW_LABEL, mm_samantha_totals, quick_glance, grid_labels)

        # --------------------------------------------------------------
        # Block 27: Google Sales # (NEW - round 5 - existing closed-won
        # Sales logic + deal-level source contains "Google")
        # --------------------------------------------------------------
        google_sales_extra_filters_branches = [
            [{"propertyName": deal_source_property, "operator": "CONTAINS_TOKEN", "value": GOOGLE_SOURCE_CONTAINS_VALUE}],
        ]
        google_sales_count_values, google_sales_count_totals, _google_sales_dollar_values, _google_sales_dollar_totals, google_sales_owners_seen = fetch_deal_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_deal_fetch(fetch_source_deal_period_live, frozen_master, GOOGLE_SALES_TOTAL_ROW_LABEL), (token, closed_won_date_property, DEALSTAGE_PROPERTY, closed_won_dealstage_values, deal_amount_property, deal_owner_property, owners_map, SALES_TIMEZONE, google_sales_extra_filters_branches),
        )
        google_sales_rows = build_metric_rows(GOOGLE_SALES_TOTAL_ROW_LABEL, google_sales_count_values, google_sales_count_totals, google_sales_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # Block 28: AI Sales # (NEW - round 5 - existing closed-won Sales
        # logic + deal-level source contains "AI" OR Inferred Landing
        # Page contains "chatgpt")
        #
        # FIX (round 6): the second branch is now conditional - it's only
        # added if a deal-level Inferred Landing Page property actually
        # resolved. When both properties resolve, this is byte-for-byte
        # the same two-branch list as before.
        # --------------------------------------------------------------
        ai_sales_extra_filters_branches = [
            [{"propertyName": deal_source_property, "operator": "CONTAINS_TOKEN", "value": AI_SOURCE_CONTAINS_VALUE}],
        ]
        if deal_inferred_landing_page_property:
            ai_sales_extra_filters_branches.append(
                [{"propertyName": deal_inferred_landing_page_property, "operator": "CONTAINS_TOKEN", "value": INFERRED_LANDING_PAGE_CONTAINS_VALUE}]
            )
        else:
            print(
                "WARNING: no deal-level Inferred Landing Page property resolved - 'Total AI Sales #' is running on the "
                "deal-source-contains-'AI' branch ONLY. Deals whose only AI signal is a chatgpt landing page will be "
                "MISSED, so that row (and 'Total Google + AI Sales #') may under-count. Set "
                "DEAL_INFERRED_LANDING_PAGE_PROPERTY_OVERRIDE once you know the right internal name."
            )
        ai_sales_count_values, ai_sales_count_totals, _ai_sales_dollar_values, _ai_sales_dollar_totals, ai_sales_owners_seen = fetch_deal_metric_periods(
            year_blocks_desc, quick_glance, executor,
            freeze_deal_fetch(fetch_source_deal_period_live, frozen_master, AI_SALES_TOTAL_ROW_LABEL), (token, closed_won_date_property, DEALSTAGE_PROPERTY, closed_won_dealstage_values, deal_amount_property, deal_owner_property, owners_map, SALES_TIMEZONE, ai_sales_extra_filters_branches),
        )
        ai_sales_rows = build_metric_rows(AI_SALES_TOTAL_ROW_LABEL, ai_sales_count_values, ai_sales_count_totals, ai_sales_owners_seen, quick_glance, grid_labels, year_total_labels)

        # --------------------------------------------------------------
        # NEW: Daily tab - Calls / Meetings / Sales, one column per
        # calendar day (see 'Daily tab' config section above for the
        # confirmed filters). Hours is deliberately left blank - no
        # property was given for it. Reuses the same already-resolved
        # properties/filters as the existing Meetings/Calls/Sales
        # blocks above - none of those blocks are touched.
        # --------------------------------------------------------------
        daily_periods, daily_columns = build_daily_period_columns(today)

        daily_calls_values, daily_calls_totals, daily_calls_owners_seen = fetch_daily_metric_periods(
            daily_periods, executor,
            freeze_fetch(fetch_period_live_engagement, frozen_daily, DAILY_CALLS_TOTAL_ROW_LABEL), (token, "calls", calls_date_property, calls_owner_property, owners_map, None, CALLS_TIMEZONE),
        )
        daily_calls_rows = build_daily_metric_rows(DAILY_CALLS_TOTAL_ROW_LABEL, daily_calls_values, daily_calls_totals, daily_calls_owners_seen, daily_columns)

        daily_meetings_values, daily_meetings_totals, daily_meetings_owners_seen = fetch_daily_metric_periods(
            daily_periods, executor,
            freeze_fetch(fetch_period_live_engagement, frozen_daily, DAILY_MEETINGS_TOTAL_ROW_LABEL), (token, "meetings", meetings_date_property, meetings_owner_property, owners_map, meetings_extra_filters, MEETINGS_TIMEZONE),
        )
        daily_meetings_rows = build_daily_metric_rows(DAILY_MEETINGS_TOTAL_ROW_LABEL, daily_meetings_values, daily_meetings_totals, daily_meetings_owners_seen, daily_columns)

        daily_sales_count_values, daily_sales_count_totals, _daily_sales_dollar_values, _daily_sales_dollar_totals, daily_sales_owners_seen = fetch_daily_deal_metric_periods(
            daily_periods, executor,
            freeze_deal_fetch(fetch_deal_period_live, frozen_daily, DAILY_SALES_TOTAL_ROW_LABEL), (token, closed_won_date_property, DEALSTAGE_PROPERTY, closed_won_dealstage_values, deal_amount_property, deal_owner_property, owners_map, SALES_TIMEZONE),
        )
        daily_sales_rows = build_daily_metric_rows(DAILY_SALES_TOTAL_ROW_LABEL, daily_sales_count_values, daily_sales_count_totals, daily_sales_owners_seen, daily_columns)

        daily_hours_owners = daily_calls_owners_seen | daily_meetings_owners_seen | daily_sales_owners_seen
        daily_hours_rows = build_daily_blank_rows(DAILY_HOURS_TOTAL_ROW_LABEL, daily_hours_owners, daily_columns)

    # ------------------------------------------------------------------
    # Blocks 12-15 (+ 25-26): Derived ratio / sum metrics (NEW) - pure
    # math on values/totals already fetched above. No additional
    # HubSpot calls, so these run outside the ThreadPoolExecutor's `with`
    # block.
    # ------------------------------------------------------------------
    avg_sale_rows = build_ratio_rows(
        AVG_SALE_ROW_LABEL, sales_dollar_values, sales_count_values, sales_dollar_totals, sales_count_totals,
        quick_glance, grid_labels, as_currency=True,
    )
    # CORRECTED: numerator is the combined Total Sales # (new business +
    # renewals), not New Business # - per explicit correction. as_percentage
    # already multiplies by 100 internally (see build_ratio_rows.fmt()).
    sales_per_lead_rows = build_ratio_rows(
        SALES_PER_LEAD_ROW_LABEL, sales_count_values, leads_period_values, sales_count_totals, leads_period_totals,
        quick_glance, grid_labels, as_percentage=True,
    )
    meetings_per_lead_rows = build_ratio_rows(
        MEETINGS_PER_LEAD_ROW_LABEL, meetings_period_values, leads_period_values, meetings_period_totals, leads_period_totals,
        quick_glance, grid_labels, as_percentage=True,
    )
    # CORRECTED: numerator is the combined Total Sales #, not New Business #.
    sales_per_meeting_rows = build_ratio_rows(
        SALES_PER_MEETING_ROW_LABEL, sales_count_values, meetings_period_values, sales_count_totals, meetings_period_totals,
        quick_glance, grid_labels, as_percentage=True,
    )

    # Block 25: Total Organic Leads Assigned = Google Leads + AI/ChatGPT
    # Leads, period-by-period. Total-only (see build_sum_rows docstring).
    organic_leads_rows = build_sum_rows(ORGANIC_LEADS_TOTAL_ROW_LABEL, [google_leads_totals, ai_leads_totals], quick_glance, grid_labels)

    # Block 26: Appt Set: Show Rate = Appt Set Meetings Completed / Appt
    # Set, owner level. Both source blocks key off the same display_property
    # (First Assigned Contact Owner by name) and the same leads_owner_roster,
    # so per-owner matching here is more reliable than the Sales/Leads and
    # Meetings/Leads ratios above (which cross two different owner-name
    # sources) - see build_ratio_rows' owner-matching caveat regardless.
    appt_set_show_rate_rows = build_ratio_rows(
        APPT_SET_SHOW_RATE_ROW_LABEL, meetings_completed_values, appt_set_values, meetings_completed_totals, appt_set_totals,
        quick_glance, grid_labels, as_percentage=True,
    )

    # Block 29 (NEW - round 5): Total Google + AI Sales # = Google Sales #
    # + AI Sales #, period-by-period. Total-only (see build_sum_rows
    # docstring) - pure addition, no additional HubSpot calls.
    google_ai_sales_total_rows = build_sum_rows(GOOGLE_AI_SALES_TOTAL_ROW_LABEL, [google_sales_count_totals, ai_sales_count_totals], quick_glance, grid_labels)

    # Block 30 (NEW - round 5): Close Rate of Google Leads = Google
    # Sales # / Total Google Leads Assigned (existing block 16, above -
    # not modified). See the ASSUMPTION note on GOOGLE_CLOSE_RATE_ROW_LABEL
    # for the numerator/denominator direction.
    google_close_rate_rows = build_ratio_rows(
        GOOGLE_CLOSE_RATE_ROW_LABEL, google_sales_count_values, google_leads_values, google_sales_count_totals, google_leads_totals,
        quick_glance, grid_labels, as_percentage=True,
    )

    # ------------------------------------------------------------------
    # Assemble all 30 blocks, each separated by a spacer row.
    # ------------------------------------------------------------------
    spacer_row = [""] * len(header_row)
    data_rows = (
        leads_rows + [spacer_row]
        + meetings_rows + [spacer_row]
        + calls_rows + [spacer_row]
        + sales_count_rows + [spacer_row]
        + sales_dollar_rows + [spacer_row]
        + new_business_count_rows + [spacer_row]
        + new_business_dollar_rows + [spacer_row]
        + renewals_count_rows + [spacer_row]
        + renewals_dollar_rows + [spacer_row]
        + old_lead_count_rows + [spacer_row]
        + old_lead_dollar_rows + [spacer_row]
        + avg_sale_rows + [spacer_row]
        + sales_per_lead_rows + [spacer_row]
        + meetings_per_lead_rows + [spacer_row]
        + sales_per_meeting_rows + [spacer_row]
        + google_leads_rows + [spacer_row]
        + ai_leads_rows + [spacer_row]
        + organic_leads_rows + [spacer_row]
        + appt_set_rows + [spacer_row]
        + appt_set_high_income_rows + [spacer_row]
        + appt_set_low_income_rows + [spacer_row]
        + new_lead_no_appt_rows + [spacer_row]
        + appt_set_meetings_completed_rows + [spacer_row]
        + appt_set_show_rate_rows + [spacer_row]
        + mm_recruits_rows + [spacer_row]
        + mm_recruits_samantha_rows + [spacer_row]
        + google_sales_rows + [spacer_row]
        + ai_sales_rows + [spacer_row]
        + google_ai_sales_total_rows + [spacer_row]
        + google_close_rate_rows
    )

    leads_total_row_idx = 1  # sheet row index (0-based); row 0 is the header
    meetings_block_start = leads_total_row_idx + len(leads_rows) + 1
    calls_block_start = meetings_block_start + len(meetings_rows) + 1
    sales_count_block_start = calls_block_start + len(calls_rows) + 1
    sales_dollar_block_start = sales_count_block_start + len(sales_count_rows) + 1
    new_business_count_block_start = sales_dollar_block_start + len(sales_dollar_rows) + 1
    new_business_dollar_block_start = new_business_count_block_start + len(new_business_count_rows) + 1
    renewals_count_block_start = new_business_dollar_block_start + len(new_business_dollar_rows) + 1
    renewals_dollar_block_start = renewals_count_block_start + len(renewals_count_rows) + 1
    old_lead_count_block_start = renewals_dollar_block_start + len(renewals_dollar_rows) + 1
    old_lead_dollar_block_start = old_lead_count_block_start + len(old_lead_count_rows) + 1
    avg_sale_block_start = old_lead_dollar_block_start + len(old_lead_dollar_rows) + 1
    sales_per_lead_block_start = avg_sale_block_start + len(avg_sale_rows) + 1
    meetings_per_lead_block_start = sales_per_lead_block_start + len(sales_per_lead_rows) + 1
    sales_per_meeting_block_start = meetings_per_lead_block_start + len(meetings_per_lead_rows) + 1
    google_leads_block_start = sales_per_meeting_block_start + len(sales_per_meeting_rows) + 1
    ai_leads_block_start = google_leads_block_start + len(google_leads_rows) + 1
    organic_leads_block_start = ai_leads_block_start + len(ai_leads_rows) + 1
    appt_set_block_start = organic_leads_block_start + len(organic_leads_rows) + 1
    appt_set_high_income_block_start = appt_set_block_start + len(appt_set_rows) + 1
    appt_set_low_income_block_start = appt_set_high_income_block_start + len(appt_set_high_income_rows) + 1
    new_lead_no_appt_block_start = appt_set_low_income_block_start + len(appt_set_low_income_rows) + 1
    appt_set_meetings_completed_block_start = new_lead_no_appt_block_start + len(new_lead_no_appt_rows) + 1
    appt_set_show_rate_block_start = appt_set_meetings_completed_block_start + len(appt_set_meetings_completed_rows) + 1
    mm_recruits_block_start = appt_set_show_rate_block_start + len(appt_set_show_rate_rows) + 1
    mm_recruits_samantha_block_start = mm_recruits_block_start + len(mm_recruits_rows) + 1
    google_sales_block_start = mm_recruits_samantha_block_start + len(mm_recruits_samantha_rows) + 1
    ai_sales_block_start = google_sales_block_start + len(google_sales_rows) + 1
    google_ai_sales_total_block_start = ai_sales_block_start + len(ai_sales_rows) + 1
    google_close_rate_block_start = google_ai_sales_total_block_start + len(google_ai_sales_total_rows) + 1

    total_row_indices = [
        leads_total_row_idx, meetings_block_start, calls_block_start,
        sales_count_block_start, sales_dollar_block_start,
        new_business_count_block_start, new_business_dollar_block_start,
        renewals_count_block_start, renewals_dollar_block_start,
        old_lead_count_block_start, old_lead_dollar_block_start,
        avg_sale_block_start, sales_per_lead_block_start,
        meetings_per_lead_block_start, sales_per_meeting_block_start,
        google_leads_block_start, ai_leads_block_start, organic_leads_block_start,
        appt_set_block_start, appt_set_high_income_block_start, appt_set_low_income_block_start,
        new_lead_no_appt_block_start, appt_set_meetings_completed_block_start, appt_set_show_rate_block_start,
        mm_recruits_block_start, mm_recruits_samantha_block_start,
        google_sales_block_start, ai_sales_block_start, google_ai_sales_total_block_start, google_close_rate_block_start,
    ]
    spacer_row_indices = [
        leads_total_row_idx + len(leads_rows),
        meetings_block_start + len(meetings_rows),
        calls_block_start + len(calls_rows),
        sales_count_block_start + len(sales_count_rows),
        sales_dollar_block_start + len(sales_dollar_rows),
        new_business_count_block_start + len(new_business_count_rows),
        new_business_dollar_block_start + len(new_business_dollar_rows),
        renewals_count_block_start + len(renewals_count_rows),
        renewals_dollar_block_start + len(renewals_dollar_rows),
        old_lead_count_block_start + len(old_lead_count_rows),
        old_lead_dollar_block_start + len(old_lead_dollar_rows),
        avg_sale_block_start + len(avg_sale_rows),
        sales_per_lead_block_start + len(sales_per_lead_rows),
        meetings_per_lead_block_start + len(meetings_per_lead_rows),
        sales_per_meeting_block_start + len(sales_per_meeting_rows),
        google_leads_block_start + len(google_leads_rows),
        ai_leads_block_start + len(ai_leads_rows),
        organic_leads_block_start + len(organic_leads_rows),
        appt_set_block_start + len(appt_set_rows),
        appt_set_high_income_block_start + len(appt_set_high_income_rows),
        appt_set_low_income_block_start + len(appt_set_low_income_rows),
        new_lead_no_appt_block_start + len(new_lead_no_appt_rows),
        appt_set_meetings_completed_block_start + len(appt_set_meetings_completed_rows),
        appt_set_show_rate_block_start + len(appt_set_show_rate_rows),
        mm_recruits_block_start + len(mm_recruits_rows),
        mm_recruits_samantha_block_start + len(mm_recruits_samantha_rows),
        google_sales_block_start + len(google_sales_rows),
        ai_sales_block_start + len(ai_sales_rows),
        google_ai_sales_total_block_start + len(google_ai_sales_total_rows),
    ]
    # Only blocks whose cell values are RAW numeric dollar amounts (not
    # already-formatted ratio strings) need the Sheets-level CURRENCY
    # numberFormat override - Sales $, New Business $, Renewals $, and
    # Old-Lead-Sales $. Avg Sale $ / Appt Set: Show Rate are ratio rows and
    # already carry their formatting in the string itself (see
    # build_ratio_rows), so they're excluded here. None of the round-2
    # blocks are dollar counts either (all are contact counts or a %).
    currency_row_ranges = [
        (sales_dollar_block_start, sales_dollar_block_start + len(sales_dollar_rows)),
        (new_business_dollar_block_start, new_business_dollar_block_start + len(new_business_dollar_rows)),
        (renewals_dollar_block_start, renewals_dollar_block_start + len(renewals_dollar_rows)),
        (old_lead_dollar_block_start, old_lead_dollar_block_start + len(old_lead_dollar_rows)),
    ]

    # Owner-row ranges for row-group collapsing (NEW): for every block,
    # everything after its Total row up to (but not including) its own
    # length - i.e. exactly that block's owner rows, never the Total row
    # itself and never the next block's rows. Built from the same
    # total_row_indices list plus each block's own row-count, in the same
    # order they were assembled into data_rows above. Total-only blocks
    # (AI Leads, Organic Leads, MM Recruits, MM Recruits - Samantha) have
    # a row_count of 1, so start_idx+1 == start_idx+row_count and no row
    # group gets created for them (apply_row_groups skips ranges where
    # end_row <= start_row) - nothing to collapse when there's no owner
    # detail underneath.
    block_row_counts = [
        len(leads_rows), len(meetings_rows), len(calls_rows),
        len(sales_count_rows), len(sales_dollar_rows),
        len(new_business_count_rows), len(new_business_dollar_rows),
        len(renewals_count_rows), len(renewals_dollar_rows),
        len(old_lead_count_rows), len(old_lead_dollar_rows),
        len(avg_sale_rows), len(sales_per_lead_rows),
        len(meetings_per_lead_rows), len(sales_per_meeting_rows),
        len(google_leads_rows), len(ai_leads_rows), len(organic_leads_rows),
        len(appt_set_rows), len(appt_set_high_income_rows), len(appt_set_low_income_rows),
        len(new_lead_no_appt_rows), len(appt_set_meetings_completed_rows), len(appt_set_show_rate_rows),
        len(mm_recruits_rows), len(mm_recruits_samantha_rows),
        len(google_sales_rows), len(ai_sales_rows), len(google_ai_sales_total_rows), len(google_close_rate_rows),
    ]
    owner_row_ranges = [
        (start_idx + 1, start_idx + row_count)
        for start_idx, row_count in zip(total_row_indices, block_row_counts)
    ]

    worksheet = write_to_sheet(spreadsheet, header_row, data_rows)
    apply_column_groups(spreadsheet, worksheet, quick_glance_labels, year_blocks_desc)
    apply_formatting(spreadsheet, worksheet, len(quick_glance_labels), year_blocks_desc, total_row_indices, spacer_row_indices, currency_row_ranges)
    apply_row_groups(spreadsheet, worksheet, owner_row_ranges)

    # ------------------------------------------------------------------
    # NEW: Daily tab assembly + write (Calls / Meetings / Sales / Hours,
    # one column per calendar day) - written to the SAME spreadsheet as
    # a separate 'Daily' worksheet. Independent of everything above;
    # nothing here changes the Master Metric Sheet tab.
    # ------------------------------------------------------------------
    daily_header_row = ["Owner"] + [col.label if col is not None else "" for col in daily_columns]
    daily_spacer_row = [""] * len(daily_header_row)
    daily_data_rows = (
        daily_calls_rows + [daily_spacer_row]
        + daily_meetings_rows + [daily_spacer_row]
        + daily_sales_rows + [daily_spacer_row]
        + daily_hours_rows
    )

    daily_calls_total_idx = 1
    daily_meetings_total_idx = daily_calls_total_idx + len(daily_calls_rows) + 1
    daily_sales_total_idx = daily_meetings_total_idx + len(daily_meetings_rows) + 1
    daily_hours_total_idx = daily_sales_total_idx + len(daily_sales_rows) + 1

    daily_total_row_indices = [daily_calls_total_idx, daily_meetings_total_idx, daily_sales_total_idx, daily_hours_total_idx]
    daily_spacer_row_indices = [
        daily_calls_total_idx + len(daily_calls_rows),
        daily_meetings_total_idx + len(daily_meetings_rows),
        daily_sales_total_idx + len(daily_sales_rows),
    ]

    daily_worksheet = write_daily_tab(spreadsheet, daily_header_row, daily_data_rows)
    apply_daily_formatting(spreadsheet, daily_worksheet, daily_total_row_indices, daily_spacer_row_indices)

    total_cells = _FREEZE_STATS["frozen"] + _FREEZE_STATS["fetched"]
    if total_cells:
        pct = 100.0 * _FREEZE_STATS["frozen"] / total_cells
        print(
            f"\nFreeze summary: {_FREEZE_STATS['frozen']} period-fetches reused from the previous run, "
            f"{_FREEZE_STATS['fetched']} fetched live ({pct:.0f}% avoided)."
        )
        if _FREEZE_STATS["frozen"] == 0 and FREEZE_COMPLETED_PERIODS:
            print(
                "  (Nothing was frozen. On the FIRST run after enabling this there is no previous\n"
                "   sheet to reuse, so everything is fetched - the next run is the fast one.)"
            )


if __name__ == "__main__":
    main()
