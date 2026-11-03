# CRM and masked calling: requirements, options and cost

Status: draft for decision. Written 2026-11-02. Owner: D-SAP. Nothing here is built.

This is the business and product requirements document (BRD and PRD) for the lead desk behind iitjeekota.com, the options for building or buying it, what each costs, and a technical overview of the recommended design. The rest of the backend plan is in `docs/setup/next-steps.md`, section 5.

## 0. How to read this document

- **Evidence grade.** Most prices below come from third-party comparison blogs and reseller pages, found by web search on 2026-11-02. They disagree with each other. Treat every price as an estimate to confirm in a written quote. Where a claim comes from the vendor's own documentation, the text says so.
- **Not legal advice.** Telecom, call recording and data protection points are listed as questions for the Phase 1 legal review, not as conclusions.
- **Estimates are mine.** Build effort and the worked example in section 9 are my estimates from the requirements, not quotes.

## 1. Purpose and scope

### 1.1 Problem
Families enquire by form, phone or WhatsApp. Today there is no single record of who enquired, who spoke to them, what was said, or whether they enrolled. Telecallers can see and copy phone numbers. A lead can be lost, handled twice, or taken out of the institute.

### 1.2 Goal
One login-protected lead desk, on its own domain, where:
1. Every enquiry from the website, calls and walk-ins becomes one lead record.
2. Telecallers work only the leads of their own centre, and never see a real phone number.
3. Outgoing calls start from the lead record. The system picks the number and dials. The telecaller sees a masked number or a hash.
4. Parents can call one dedicated number. A parent who has spoken to an executive before reaches that executive, and the executive sees the earlier call summaries while the phone rings.
5. Calls are recorded, transcribed in Hindi, Marathi and English, and summarised.
6. Management sees conversion, workload and call quality, and is alerted when a telecaller's behaviour looks like data theft.

### 1.3 In scope
Lead and contact records, pipeline and conversion status, and masked outbound calling. Single-number inbound routing, call recording and AI summary. Role-based access by centre, dashboards, audit and alerts, and the link from the website's enquiry form.

### 1.4 Out of scope for the first release
Fee collection and receipts, student records and attendance, marketing email campaigns, WhatsApp chatbots, and a separate native mobile app for the desk. The desk itself is a web application that installs on a phone like an app (section 10). Calling uses the provider's own app.

### 1.5 Decisions made and assumptions
Confirmed by D-SAP on 2026-11-02:
- The desk lives at `admin.dsapghule.com`, a separate domain from the public site (iitjeekota.com), and D-SAP owns it.
- Telecallers use their own mobile phones, by logging in to the provider's app (the way Heyo or Superfone work). A desk phone can be added if a provider needs one.
- No automated or recorded voice. A real person always makes and receives the call. AI is limited to assistance and summaries.
- D-SAP needs a new dedicated number from the chosen provider. The existing +91 22 6971 9828 is on Heyo, which has no call masking. Changing the public number has website consequences (section 6.1).

Confirmed by D-SAP later on 2026-11-02:
- Telecallers have Microsoft (institute) email addresses, so sign-in uses Microsoft Entra ID.
- 2 to 3 telecallers per centre, so 4 to 6 at launch.
- The super admin can listen to recordings and review misuse flags.
- The Heyo number stays in use.
- Telecallers install the provider's app on their personal phones, and can receive calls on the phone, but must not see any number.
- The new number should be in the +91 22 or +91 20 series.
- The provider is chosen by the pilot. Superfone, MyOperator, Knowlarity, Tata Tele, Interakt and ElevenLabs may be tested, and others added.

Still assumed:
- Calls go to and from Indian numbers only, on Indian telecom networks.
- Two centres at launch (New Sangvi and Wakad), with more possible.

## 2. Business requirements

| ID | Requirement | Why | Measure |
|---|---|---|---|
| BR-1 | Every enquiry is captured once, with its source and consent | No lost or double-handled leads | 0 leads without a record; duplicate rate under 2% |
| BR-2 | A telecaller can work a lead without ever holding its real phone number | Stops lead theft and misuse | No real number in any screen, export, log or API answer for the telecaller role |
| BR-3 | Access follows the centre: a Wakad telecaller sees Wakad leads only | Limits what any one account can leak | Cross-centre access attempts are blocked and logged |
| BR-4 | A returning parent reaches the same executive | Continuity; fewer repeated questions | At least 90% of repeat inbound calls reach the assigned executive within the window |
| BR-5 | Management can see conversion from enquiry to admission, by source, centre and telecaller | Decisions on spend and staffing | Funnel report available daily |
| BR-6 | Call content is available as a summary in the three site languages | Quality control and hand-over | A summary on every recorded call over 30 seconds |
| BR-7 | The institute can detect and prove misuse | Deterrence and evidence | Alerts on risky behaviour; an audit log nobody can edit |
| BR-8 | The solution follows Indian telecom and data protection rules | Legal exposure | Phase 1 compliance matrix signed off before launch |
| BR-9 | The cost stays predictable for 5 to 15 telecallers | Small institute budget | Monthly run cost within an agreed cap (section 9) |

## 3. Users and roles (RBAC)

Access is by role and by centre. A person has one role at one or more centres.

| Role | Who | Sees | Can do | Cannot do |
|---|---|---|---|---|
| Telecaller | Counsellor at a centre | Own assigned leads, masked number or hash, their own call summaries, own targets | Start a call, add notes, change lead status, book a visit, request a reassignment | See a real number, export, search other telecallers' leads, download recordings, bulk view |
| Team lead | Senior counsellor, one centre | All leads of the centre, summaries, flags for the centre, call recordings of the centre | Reassign leads, approve status changes, listen to recordings in the browser | See real numbers, export |
| Centre head | Owner of a centre | Centre dashboards, all centre leads, flags | Same as team lead, plus set targets and working hours | See real numbers, other centres' data |
| Quality reviewer | Internal auditor | Flags, transcripts, summaries across centres, the audit log | Mark a flag as confirmed or cleared | Edit leads, start calls |
| Super admin | Owner or a named trustee | Everything, including real numbers | Reveal a real number after re-authentication (section 4.4), manage users, roles, numbers, retention, data requests, exports with approval | Edit or delete the audit log |
| Integration account | The website API, the telephony provider | Only the calls it needs | Create leads, post call events | Read leads |

Rules for every role: access is removed the same day a person leaves; there are no shared logins; a role change is logged.

## 4. Product requirements

### 4.1 Sign-in and access (FR-AUTH)
- FR-AUTH-1: Sign in with the institute email through the institute's identity provider (Google Workspace or Microsoft Entra, whichever the institute email runs on).
- FR-AUTH-2: Multi-factor authentication is required for every role. Super admin and team lead use a passkey or a hardware key where possible. SMS codes are not accepted for super admin.
- FR-AUTH-3: The desk sits behind Cloudflare Access, so the login page is not reachable by the public. Sessions are short, bound to the device, and end after idle time.
- FR-AUTH-4: Optional allow-list of office IP ranges for telecallers. A telecaller working from home needs a named exception.
- FR-AUTH-5: Cookies are scoped to `admin.dsapghule.com` only and never shared with the public site.

### 4.2 Leads and pipeline (FR-LEAD)
- FR-LEAD-1: One lead per parent phone number. A duplicate enquiry joins the existing lead and adds to its history.
- FR-LEAD-2: Fields: student name, class (9, 10, 11, 12, dropper), school, area, preferred centre, language, source (website form, call, WhatsApp, walk-in, referral), consent record, assigned telecaller, status, notes.
- FR-LEAD-3: Pipeline statuses with the reason for each exit. Starting set: New, Contacted, Interested, Visit booked, Visited, Offer or scholarship discussed, Admission, Not interested (reason), Not reachable, Duplicate, Invalid. D-SAP edits this list in one data file.
- FR-LEAD-4: Follow-up tasks with due times and reminders. A lead with no activity for a set number of days is flagged to the team lead.
- FR-LEAD-5: Lead routing on creation: by area to the nearest centre, then to a telecaller by rule (round robin, load, or language). Rules are data, not code.
- FR-LEAD-6: A full timeline per lead: form submission, every call with its summary, status changes, notes, who did what.
- FR-LEAD-7: Walk-in and manual entry by a telecaller creates a lead, but the number is typed once into a field that is then masked for that user.

### 4.3 Calling out (FR-OUT)
- FR-OUT-1: A "Call" button on the lead. The system looks up the real number, chooses the correct caller number for that centre and lead, and starts the call. The telecaller never types or sees the number.
- FR-OUT-2: Connection method. The telecaller is signed in to the provider's mobile app on their own phone. Pressing Call in the desk tells the provider to start the call, and the provider connects the telecaller to the parent. The parent's number never appears on the telecaller's phone: not in the app, the phone's call log or the notifications. The parent sees the institute's number, not the telecaller's personal number. A call back to the institute number reaches the right executive (FR-IN-2).
- FR-OUT-2a: Two provider models are possible. In the app model, the call runs inside the provider's app over the internet (the Superfone model). In the bridge model, the provider rings the telecaller's mobile number from the institute's number, then the parent, and joins the two. In the bridge model the telecaller's phone only ever shows the institute's number, so hiding the parent's number is built in. In the app model it depends on what the app shows, and the docs read so far do not say. Either meets FR-OUT-2 if the provider confirms it in writing and the pilot shows it works. In the app model the provider's app must not offer a dial pad or a contact list for telecaller users.
- FR-OUT-2b: Inbound calls reach the telecaller's phone the same way. The phone shows the institute's number or the app's own call screen, never the parent's number. The pilot tests this on an Android phone and an iPhone, including the phone's own call log and notifications.
- FR-OUT-3: Calls are blocked outside allowed hours and for numbers flagged as do-not-call. Each call checks the do-not-call state first.
- FR-OUT-4: Limits per telecaller: maximum calls per hour and per day, and a minimum gap between attempts to the same lead.
- FR-OUT-5: After the call the telecaller must set a status and a short note before the next call starts.
- FR-OUT-6: Speed to first call. A new website enquiry alerts the telecaller on duty and shows a "call now" task, with a target time (for example 5 minutes in working hours). The system never places an automated or recorded call. A person always speaks.

### 4.4 Real number reveal (FR-REVEAL)
- FR-REVEAL-1: Only the super admin role can reveal a real number.
- FR-REVEAL-2: Each reveal asks the person to authenticate again with their own credential (passkey or one-time code). A shared master password is not used, because it cannot show who revealed what.
- FR-REVEAL-3: Each reveal needs a typed reason, shows the number for about 30 seconds, and writes an audit entry with who, which lead, when, and why.
- FR-REVEAL-4: The owner gets a message for every reveal. More than a set number per day raises a flag.

### 4.5 Calling in (FR-IN)
- FR-IN-1: One public number for parents to call (the "single dedicated virtual number"), shown on the website, in ads and on printed material.
- FR-IN-2: On each inbound call the system looks up the caller's number and decides:
  1. Known lead with an assigned executive, within the stickiness window: ring that executive.
  2. Assigned executive busy or off duty: ring the executive's team in the same centre, or take a message, per the rule for that lead.
  3. Known lead, no executive: ring the centre queue for that lead's area.
  4. Unknown number: create a new lead, then ring the default queue.
- FR-IN-3: While the phone rings, the executive's screen shows the lead card, the last call summaries and open follow-ups (a screen pop). The real number is not shown.
- FR-IN-4: Stickiness window and fallbacks are settings, not code.
- FR-IN-5: Missed inbound calls create a task for the assigned executive and are counted on the dashboard.
- FR-IN-6: Business hours greeting and an out-of-hours message, in Hindi, Marathi and English.

### 4.6 Call recording, transcript and summary (FR-AI)
- FR-AI-1: Every call is recorded after a spoken notice, and the recording is stored in India, encrypted.
- FR-AI-2: A transcript in the language spoken, including Hindi, Marathi and English mixed in one call.
- FR-AI-3: A summary of 5 to 8 lines in English with the parent's questions, objections, student details mentioned, promised actions and the suggested next status. A Hindi or Marathi version on request.
- FR-AI-4: The summary is attached to the lead and shown to the next executive.
- FR-AI-5: Telecallers hear nothing of other executives' recordings. Team leads and reviewers play recordings in the browser. Nobody but the super admin can download a recording.
- FR-AI-6: A person can correct a summary. The original is kept.
- FR-AI-7: Recording retention is set in data and enforced by a job (a rule from Phase 1).
- FR-AI-8: Assistance for the telecaller, never a voice on the call. Before a call: a short brief of the lead's history and open follow-ups. After a call: a suggested next status, a draft follow-up message for the telecaller to edit and send, and a list of questions the parent asked that are still open. Live prompts during a call are optional for a later release.

### 4.7 Misuse detection (FR-GUARD)
The aim is that a telecaller cannot take the data out, and that an attempt is seen quickly.

Preventive:
- FR-GUARD-1: Real numbers are never sent to the telecaller's browser. The masked value is generated on the server.
- FR-GUARD-2: No export, no copy-all, no print for telecaller and team lead roles. The screen carries a watermark of the user's name and time.
- FR-GUARD-3: A telecaller sees only assigned leads, no global search, and a cap on how many lead cards can be opened per hour.
- FR-GUARD-4: Recordings stream with short-lived links. No download button.
- FR-GUARD-5: Test leads (canary records) with numbers owned by the institute are placed in each telecaller's list. If anyone calls one of those numbers from outside the system, the institute sees it.

Detective (alerts to the team lead, the centre head and the quality reviewer):
- FR-GUARD-6: A transcript check for a telecaller asking the parent for another number, a WhatsApp number, or to call back on a personal number. Also for the parent saying they do not want to enquire while a new lead or number is recorded anyway.
- FR-GUARD-7: Unusual patterns: many lead cards opened with no call, opening leads outside shift hours, repeated failed reveal or export attempts, many short calls, a sudden rise in leads marked invalid or duplicate.
- FR-GUARD-8: Each flag shows the evidence (the clip, the transcript lines, the access log) and a reviewer marks it confirmed or cleared.
- FR-GUARD-9: An immutable audit log of every view, call, reveal, change and login.

Honest limits: nothing here stops a person photographing a screen, or writing down a number they heard on a call. Masking removes the number from the screen, but a parent can still say a number aloud. The detection and the watermark reduce the risk and give evidence. They do not remove it.

### 4.8 Dashboards and reports (FR-DASH)
- FR-DASH-1: Funnel from enquiry to admission, by source, centre, telecaller, class and week.
- FR-DASH-2: Speed to first call, number of attempts per lead, contact rate, talk time, missed inbound calls.
- FR-DASH-3: Follow-ups due and overdue. Leads with no activity.
- FR-DASH-4: Telecaller scorecards (calls, connected calls, visits booked, admissions) visible to the telecaller themselves and to their lead.
- FR-DASH-5: Call quality: summary themes, objections raised, the share of calls with flags.
- FR-DASH-6: Source and spend view: which website pages and campaigns create leads that convert. Links to the website's page and area data.

### 4.9 Website link (FR-SITE)
- FR-SITE-1: The enquiry form on iitjeekota.com posts to the backend API (`POST /v1/leads`), which creates the lead and its consent record.
- FR-SITE-2: The website never receives lead data back. The public site and the desk share nothing except the API.
- FR-SITE-3: The page, area and language the enquiry came from are stored with the lead.

### 4.10 Non-functional requirements (NFR)
- NFR-1: Data stays in India: database, recordings, transcripts and backups. This includes the speech and summary services, or the choice is recorded with a legal opinion.
- NFR-2: Personal data columns are encrypted. Keys are in a secret manager. Logs hold no personal data.
- NFR-3: Availability target for inbound routing: the provider's fallback (a plain ring group) must work if our service is down.
- NFR-4: The routing decision for an inbound call answers in under 500 ms, or the provider falls back.
- NFR-5: Backups daily with a tested restore. Audit log kept for the period Phase 1 sets.
- NFR-6: The desk works on a laptop browser and on a phone browser. The Content Security Policy rules of the main site apply to the desk too.
- NFR-7: Every setting a manager might change (statuses, windows, limits, routing rules, retention, working hours) is data, not code.

## 5. Key flows

### 5.1 Outbound masked call
1. The telecaller opens a lead and presses Call.
2. The API checks role, centre, working hours, do-not-call and rate limits.
3. The API decrypts the real number inside the server only. It asks the telephony provider to connect the telecaller, signed in to the provider's app, to the parent. The parent sees the centre's number.
4. The provider reports the call state and the recording by webhook. The API stores them.
5. A worker transcribes the recording, writes the summary, runs the misuse checks, and attaches everything to the lead.
6. The telecaller sets a status and a note.

### 5.2 Inbound call to the single number
1. A parent calls the dedicated number.
2. The provider asks the API who should get the call, sending the caller number and the number called.
3. The API finds the lead by a keyed hash of the caller's number, applies the stickiness rule, and answers with the executive's phone or a queue.
4. The provider rings that phone. At the same moment the API pushes a screen pop to the executive's desk with the lead card and the last summaries.
5. After the call, the same steps as 5.1 steps 4 to 6.

### 5.3 Lead to admission
New, then Contacted, Interested, Visit booked, Visited, Offer discussed, Admission. Each move records who and why. An exit state needs a reason. Admission is entered by the centre head after the fee step outside this system.

## 6. Rules and constraints that shape the design

These need a lawyer and the telecom provider to confirm. The sources below are mostly news and vendor pages.

- **Numbers and series.** Indian rules separate promotional calls (140 series), service and transactional calls (160 series for regulated entities, landline-style numbers for others) and ordinary 10-digit numbers. Plivo's India documentation says the 160 series is limited to banks and similar regulated entities and that landline-style numbers such as 022 and 080 are for service and transactional calls. An enquiry callback is probably a service call, but this must be confirmed. The institute's listed number starts with 22 (Mumbai), while the centres are in Pune (020). Ask the provider which number type and which city code D-SAP can get.
- **Calls stay in India.** Plivo documents that both legs of an India call must start and end inside India and that traffic must be anchored in India. Some sources describe domestic internet calling to Indian mobiles as restricted. Yet app-based business numbers exist: the Play Store listing for [Superfone](https://play.google.com/store/apps/details?id=com.superfone&hl=en_IN) says it is licensed with the Department of Telecom and works without a SIM. So the app model is workable when the provider holds the licence. Ask each provider for the licence it relies on and how its app routes the call.
- **Masked caller ID.** Sources disagree on whether showing a virtual number as caller ID is allowed. Using a number allocated to D-SAP by a licensed provider after KYC is the safe reading. Showing a number that D-SAP was not given is not.
- **Do-not-call and consent.** TRAI's anti-spam rules changed again in 2026 (third amendment, stages from October to December 2026, per a vendor summary). Consent for the call and for the recording must be collected on the form and by a spoken notice.
- **Data protection.** Consent, purpose, retention, parental consent for under 18 and breach reporting under the DPDP Act and Rules. Telecaller access and masking support data minimisation.

### 6.1 Changing the public phone number

The number on iitjeekota.com, in the structured data, on the Google Business Profiles and on printed material is today +91 22 6971 9828. A new number is a controlled change:
1. Update the phone fact in `packages/site/facts.json`. The footer, contact page, call buttons and structured data follow from the facts.
2. Update both Google Business Profiles and any listings, so the business details match everywhere.
3. Keep the old Heyo number active and forwarding to the new number for an agreed overlap, so printed material and old links still reach someone.
4. Do the change in one release, after the provider has delivered and tested the new number. Until then the site keeps the current number.

## 7. Market research (2026-11-02)

Prices are in rupees before 18% GST unless stated. "Per agent" means per telecaller seat.

### 7.1 Indian cloud telephony providers (virtual numbers, masked calls, recording)

| Provider | What is documented | Reported price | Notes for D-SAP |
|---|---|---|---|
| [Exotel](https://developer.exotel.com/docs/advanced-config/number-masking-setup) | Vendor docs: click-to-call, webhooks, [Lead Assist](https://developer.exotel.com/api/lead-assist) (privacy masking through virtual numbers, separate API, must be enabled by the account manager), Conversational Intelligence (CQA), WebRTC SDK, MCP server. [Frappe CRM](https://docs.frappe.io/crm/exotel) has a native Exotel integration (click-to-call, call log, recording). | Reported plans: Dabbler about 9,999 for 5 months (3 agents, 1 number), Believer about 19,999, Influencer about 49,499 or 49,999. Per-minute rates in one guide, called historical: 0.40 local incoming, 0.75 inter-circle incoming, 0.80 local outgoing, 1.15 national outgoing. Sources: [Techjockey](https://www.techjockey.com/detail/exotel-call-recording-software), [Dialnexa](https://dialnexa.com/blogs/exotel-pricing/), [Bonvoice](https://bonvoice.com/insights/exotel-pricing-vs-bonvoice/). | Strongest documented API for what we need. Marathi support in its AI features is not confirmed. Exotel's own pricing page does not show prices. |
| [MyOperator](https://myoperator.com/sticky-agent) | Documented [sticky agent](https://support.myoperator.com/portal/en/kb/articles/what-is-a-sticky-agent): a returning caller reaches the agent who handled the last call, within a time window, in a strict or a loose mode. | Bundles reported: 5,000 or 15,000 a month for 10 users, billed yearly; one source says from 2,500 a month for 3 users. | Closest to FR-IN-2 as a built-in feature. Its public developer pages could not be read, so click-to-call API and masking are unconfirmed (section 7.6). |
| Knowlarity (now part of Gupshup) | Cloud telephony with lead management. Third-party guides show a click-to-call call with an agent number and a business number, and a call log pushed after each call. I found no official API reference. | One source: 1,999 per agent a month inbound, 2,999 with outbound, 3,499 with lead management. Another: from 1,499. A third: quote only. | Confirm sticky routing and masking. |
| Ozonetel (CloudAgent) | Contact centre platform. Its own blog says AI transcription and summaries are on the Standard tier; a competitor's comparison says it has none. | About 1,900 to 2,500 per agent a month, or $25 to $55; not published by the vendor. | Ask for a demo on Marathi calls. |
| [Tata Smartflo](https://docs.smartflo.tatatelebusiness.com/docs/api-dialplan-use-cases) | Cloud contact centre from Tata with public developer docs: an API dialplan (it asks our server who gets each inbound call), click-to-call, call records with recording links, webhooks, and mobile apps. | About 1,500 to 3,500 per agent a month with numbers and minutes extra, or a quote. | The closest documented match to per-call routing by our API (section 7.6). Masking from the agent is not documented. Sales-led. |
| Interakt | A WhatsApp business platform, not a number provider. It offers WhatsApp voice calls from its dashboard, with call routing and AI summaries. | Call prices not found. | It does not sell a +91 22 or 20 number. At most an extra channel for parents who prefer WhatsApp. Needs the Cloud API, a daily limit of at least 2,000 recipients, and is capped at 100 connected calls per day per number. |
| ElevenLabs | A voice AI platform. Phone numbers come from Twilio or a SIP trunk (Exotel, Plivo and others). | Not researched. | It is built for automated agents, which D-SAP ruled out. Its API does not issue Indian numbers. For India, its docs say to use an India-region account arranged with their sales. Its speech to text can be a candidate in the pilot, unconfirmed for Marathi. |
| Servetel | Small-business telephony. | From about 999 to 1,500 a month. | Cheap entry; depth unknown. |
| [Superfone](https://www.superfone.in/) | App-based business number with no SIM, shared by a team. Listings mention call recording, IVR, number masking, and CRM and WhatsApp add-ons. The Play Store listing says it is licensed with the Department of Telecom. This is the app model D-SAP described. | About 599 a month for 1 number and 3 users (one comparison site). | Public developer docs exist (section 7.6). Click-to-call API rings the agent's app, then the app calls the parent, and the parent sees the business number. Not documented: number masking in the app, per-call inbound routing without a live audio stream, 020 or 022 numbers. Click-to-call is a paid add-on and the voice API needs a request to Superfone. |
| Heyo | Landline-style numbers with a city code, an app for the team. D-SAP uses it now. | About 300 a month for 2 users (one comparison site). | D-SAP reports it has no call masking, so it cannot be the calling layer. I found nothing on a Heyo API. |
| Acefone, Fonada, Edesy and similar | Vendors that advertise number masking and click-to-call. Edesy lists a click-to-call API at 1.50 a minute. Acefone describes two-way masking with the customer's number hidden from the agent in the CRM. | Mostly quote only. | Add to the quote round if the first shortlist fails the pilot. Their claims are vendor marketing. |
| [Plivo](https://www.plivo.com/docs/voice/concepts/india-calling) | Detailed India calling rules: KYC, India-region account, both legs in India, number series limits. | Not found. | Developer platform: a build, not a ready desk. |
| Twilio | India guidance pages exist. | Not found; local number availability unconfirmed. | Check before considering. |

### 7.2 CRMs with built-in calling

| Product | Fit | Reported price | Concerns |
|---|---|---|---|
| [LeadSquared](https://www.capterra.com/p/130199/LeadSquared/) | Built for education and coaching admissions; IVR, lead distribution rules, telephony. Reviewers say it suits teams of 30 or more counsellors. | 1,250 (Lite), 2,500 (Pro), 4,500 to 5,000 (Super) per user a month, billed yearly. Telephony and some add-ons extra, unpriced. | Heavy for 5 to 15 seats. Number masking for telecallers and per-centre rules need written confirmation. |
| [Zoho CRM](https://maxwize.in/blog/zoho-crm-pricing-india) | Mature CRM and RBAC. | 800 (Standard), 1,400 (Professional), 2,400 (Enterprise), 2,600 (Ultimate) per user a month, yearly. | [Zoho Voice does not offer Indian numbers or domestic Indian calling](https://help.zoho.com/portal/en/kb/zoho-voice/zoho-voice-faqs/articles/zoho-voice-frequently-asked-questions), per Zoho's own help page. Calling would need an Indian provider connected on top. |
| Freshsales with Freshcaller | CRM with calling add-on. | Sources conflict: 999 to 6,399 per user a month for Freshsales; Freshcaller about 1,499 per agent a month (reseller). | Indian number availability and masking unconfirmed. |
| Kylas | Indian CRM for small sales teams. | About $175 to $250 a month flat for unlimited users (sources disagree); higher tier $1,250. | Telephony and masking depth unconfirmed. |
| TeleCRM | Built for telecaller teams. | Reported from 599 per user a month to $29; undisclosed. | Quote needed. |
| Meritto (formerly NoPaperForms) | Admissions CRM that markets to coaching businesses. | Custom; not published. | Likely sized for colleges; quote needed. |
| Salesforce, HubSpot | Enterprise CRMs. | Not researched. | Far above the need; data location unclear. |

### 7.3 Open-source CRM

[Frappe CRM](https://docs.frappe.io/crm/exotel) is open source and has a documented Exotel integration. Its cost is hosting and the work to add masking, per-centre rules, sticky routing, the guard features and the AI pipeline. I did not research Frappe Cloud or hosting prices, and I did not research Twenty or SuiteCRM.

### 7.4 AI call summary and Indian language speech

- **Speech to text.** [Sarvam AI](https://smallest.ai/blog/sarvam-ai-speech-to-text-pricing) lists about 30 an hour of audio for real-time, streaming and batch, and 45 an hour with speaker labels (batch). Its newer Saaras models are described as covering 22 Indian languages. These are the documented list prices; confirm them on sarvam.ai. Other Indian options named in sources are Gnani, ConvoZen and Convin (Convin says 70 or more languages including Marathi; price on request).
- **Accuracy.** I found no independent Marathi test on phone-quality (8 kHz) calls. Vendor figures come from clean audio. A published glossary from Gnani says phone audio, compression and mixing of languages are not covered by most public tests. So the choice of speech engine needs a pilot on D-SAP's own calls (section 11).
- **Provider-native AI.** Exotel, Ozonetel and Knowlarity offer or plan AI summaries and call scoring. Sources conflict on what each supports, and none confirmed Marathi. Treat as unconfirmed until demonstrated.
- **Own pipeline.** Recording from the provider, then a speech engine, then a language model for the summary and flags. Cost is mostly the speech minutes. I did not research language model pricing; per-call text summaries are small next to speech cost, but this needs a number before launch.

### 7.5 Microsoft Teams as the phone system

Teams can take calls from Indian numbers, but it does not fit this need.
- Per [Microsoft's own page](https://learn.microsoft.com/en-us/microsoftteams/operator-connect-india-plan), Indian numbers come through Operator Connect for India. The India-specific Teams Phone licence must be bought from a licensed Indian telecom operator, even if the person already has a Teams Phone entitlement. Users must be in Teams-only mode. Wireline numbers are tied to a network site. Teams Phone Mobile is not supported in India. Microsoft names Airtel and Tata Communications as delivery partners in India; prices are set by the partners and I found no rupee figures.
- Elsewhere the Teams Phone add-on is reported at about $10 per user a month before calling charges.
- Teams does not mask a lead's number from a user, route a returning caller to their last executive from CRM history, or flag misuse. Those would still need the same custom desk and an integration through Azure Communication Services or a similar route, which adds work.
- Institute email addresses are useful for sign-in (FR-AUTH-1) with or without Teams.

Teams is not recommended as the calling layer. It could still be used for internal staff calls.

### 7.6 What the providers' own API documents say (read 2026-11-02)

I read the public developer pages. Where a page could not be read, it says so. Only what is written there is listed. Anything not listed is unconfirmed.

| Question | Superfone | Tata Smartflo | MyOperator | Knowlarity |
|---|---|---|---|---|
| Public API docs | [Yes](https://docs.superfone.dev/docs/sfvopi/getting-started/). API key in a header. The voice API needs a request to hello@superfone.in. | [Yes](https://docs.smartflo.tatatelebusiness.com/docs/api-dialplan-use-cases). Bearer token. | Help pages only. The developer site returned an empty page or an error. | No official reference found. Third-party guides only. |
| Start a call from our desk | `GET /api/customer/click-2-call` with `customer_number` and `user_number`. The agent's app rings, then the app calls the parent. | `POST /v1/click_to_call_support`. The parent is called first, then the agent is joined. The other click-to-call endpoint was not read. | Click-to-call exists in CRM guides. No endpoint or fields found. | A click-to-call URL with `agent_number`, `sr_number` and `caller_id`, per a CRM guide. Unverified. |
| Parent sees | The business number (documented). | `caller_id` can be set. | Not found. | `caller_id` parameter. |
| Our server decides who gets an inbound call | Only through a live audio stream: our server answers, then sends a `transfer` command to an agent. The agent must be a Superfone user on the same number series. | Yes. The API dialplan: Smartflo posts to our HTTPS endpoint and we answer with `[{"transfer":{"type":"agent","data":["..."]}}]`. A timeout falls back to a set destination. The number of seconds is not stated on the page read. | Yes, in a CRM pattern: an IVR step calls our webhook, we return the counsellor, who rings first. Needs MyOperator support to switch on. Built-in sticky agent also exists. | Not found. |
| Call events | Dashboard-configured webhooks: all calls, missed call, recording available, summary ready. No signature. Failed deliveries are not retried. | Webhooks switched on by support. Two attempts. Fields include `$recording_url`, `$customer_number`, `$answered_agent_number`. | Webhook v2: call initiated, answered, ended, summary, disposition. Retries over 24 hours. Event id for idempotency. | A call log is pushed after each call, per CRM guides. |
| Recordings | `recording_url`, signed, valid up to 7 days. Deleted after 30 days by default. | `GET /v1/call/records` returns `recording_url`. | A recording URL is sent after the call. Field name not found. | Not found. |
| Agent mobile app | Yes. This is its main model. | Apps listed for Android and iOS. What they do for an agent was not read. | Not found. | Not found. |
| Hide the parent's number from the agent | Not documented. The event payloads carry the parent's number to our server only. | Not documented. | Not documented. Pop-ups in the CRM guide show the numbers. | Marketing page says masking uses proxy numbers. No API found. |
| 020 or 022 numbers | Not stated. | Not stated. | Not stated. | Not stated. |
| Price | Click-to-call is a paid add-on. No amount. | None found. | Plan names only. | Third-party estimates (section 7.1). |

What this means:
- **Nobody documents "hide the parent's number from the telecaller" as a setting.** It comes from the design. In the bridge model the telecaller's phone is called from the institute's number, so it never sees the parent's. In the app model it depends on the app. Our desk never shows the number either way.
- **Per-call routing by our API is documented by Tata Smartflo and, through a CRM pattern, by MyOperator.** Superfone needs our server to hold the live call, which adds a point of failure.
- **Webhooks are weak in places.** Superfone has no signature and no retries. Our API must check the sender, ignore duplicates, and fetch the recording again if an event is missed.
- **Interakt and ElevenLabs are not telephony providers for this need.** Keep them as optional extras (a WhatsApp calling channel, a speech engine to test).

### 7.7 Stack: bought parts and built parts

| Part | Bought or built | Why |
|---|---|---|
| Phone numbers, call legs, recording storage | Bought (a telecom provider). Only a licensed provider can issue Indian numbers. | The law, not a choice. |
| Speech to text, summary model | Bought as an API, behind an adapter | Better models appear often. |
| Lead desk, roles by centre, masking, reveal, audit, flags, routing decision, pipeline | Built | No product found that does all of these. The research above shows masking from the telecaller is not a documented setting anywhere. |
| WhatsApp and email notices | Bought as APIs, behind adapters | Same reason. |

## 8. Solution options

| | A. Custom lead desk on our API, with an Indian telephony provider | B. Off-the-shelf education CRM (for example LeadSquared) | C. Open-source CRM (Frappe) plus telephony provider, extended | D. Teams as the phone layer |
|---|---|---|---|---|
| Masked numbers for telecallers | Built to spec | Depends on vendor; confirm in writing | Must be built | Not provided |
| Per-centre RBAC | Built to spec | Usually available | Available; masking rules to add | Not provided |
| Sticky inbound routing | Built on provider webhooks, or the provider's sticky agent | Depends on vendor | Must be built | Not provided |
| Misuse flags and canaries | Built to spec | Rare; likely extra | Must be built | Not provided |
| Indic speech and summary | Choose the engine freely | Vendor's engine or an add-on | Choose freely | Not provided |
| Who holds the data | D-SAP | Vendor | D-SAP | Microsoft and the operator |
| Time to first use | Longest | Shortest | Medium | Not applicable |
| Fit for 5 to 15 telecallers | Good | Over-sized | Good | Poor |

**Recommendation.** Option A, in stages:
1. Pick the telephony provider by a pilot (section 11). Tata Smartflo, Exotel, MyOperator and Superfone are the first four to test, with Knowlarity or Ozonetel as a quote.
2. Build the lead desk on the planned API. The requirements that matter most are masking, centre-level RBAC, misuse detection and the reveal flow. Off-the-shelf CRMs treat these as extras. The ordinary CRM screens needed here are few.
3. Keep the telephony provider and the speech engine behind adapters, so either can be replaced by changing a setting.

**Fallback.** If D-SAP prefers to buy, take LeadSquared only after it confirms in writing: masking for the telecaller role, per-centre data scope, sticky inbound routing, Marathi call summaries, data stored in India, no export for telecallers, and a total price including telephony.

## 9. Cost

All figures are estimates from the sources in section 7, before 18% GST, to be replaced by quotes.

### 9.1 Monthly running cost for option A (illustrative)

Assumptions: 6 telecallers, 2 centres, about 100 hours of calls a month (6,000 minutes).

| Item | Basis | Per month |
|---|---|---|
| Telephony seats or bundle | 6 seats at 1,500 to 3,500, or an Exotel or MyOperator bundle | 9,000 to 21,000 |
| Call minutes | 6,000 minutes at the older reported rates of 0.40 to 1.15 | 2,400 to 6,900 |
| Virtual number rental | Not found | Quote |
| Speech to text | 100 hours at 30 (45 with speaker labels) | 3,000 to 4,500 |
| Summary and flags (language model) | Not researched | Quote |
| Hosting, database, backups, storage in India | Not researched | Quote |
| Cloudflare Access and email sign-in | Not researched | Quote |

For comparison, LeadSquared for 6 users at 2,500 to 5,000 is 15,000 to 30,000 a month before telephony, speech and add-ons. Zoho CRM for 6 users at 800 to 2,600 is 4,800 to 15,600 a month, plus an Indian telephony provider.

### 9.2 One-time build effort for option A (my estimate)

| Piece | Person-weeks |
|---|---|
| Sign-in, RBAC by centre, audit log | 2 to 3 |
| Leads, pipeline, tasks, routing rules | 2 to 3 |
| Telephony adapter: masked outbound, inbound routing, webhooks | 3 to 4 |
| Recording, speech, summary pipeline | 2 to 3 |
| Misuse detection and canaries | 1 to 2 |
| Dashboards | 1 to 2 |
| Security hardening, pilot and fixes | 2 |
| Total for a first release | 13 to 19 |

At one or two developers that is roughly 3 to 5 months. Multiply by D-SAP's developer rate for the build cost. Options B and C are mostly configuration and integration, which I estimate at 3 to 6 person-weeks for B and 8 to 12 for C. None of these figures includes the legal review.

## 10. Technical overview of option A

No code structure here, only the parts and how they connect.

**Surfaces**
- Public site (iitjeekota.com, static) posts enquiries to the API.
- Lead desk (`admin.dsapghule.com`) is a separate web application on its own domain, behind Cloudflare Access and institute sign-in with multi-factor authentication. It reads and writes only through the API's admin routes.
- The API is the one backend from the main plan (FastAPI, hexagonal). The desk adds admin routes, a call service and a few workers.

**Data**
- One Postgres database in India. Each row carries its centre. Postgres row-level security limits every query to the user's centres, so a coding mistake cannot cross centres.
- The phone number is stored encrypted. A keyed hash of the number is stored beside it, so the system can find a returning caller without decrypting. The telecaller's screen gets only a masked value such as `+91 ••••• ••421` or a short hash.
- Recordings and transcripts sit in encrypted storage in India. Access is through short-lived signed links, only for roles that may play them.
- The audit log is append-only and kept apart from the main data.

**The desk as an installable web app**
- The desk is one web application at `admin.dsapghule.com`, built so it installs on a phone like an app (a progressive web app: home screen icon, full screen, push alerts). It works on a laptop at the centre and on a telecaller's phone, beside the provider's calling app. A native app would need two more codebases and app store review, and gains nothing the desk needs. Revisit if push alerts on iPhone prove unreliable in the pilot. The provider's own app does the calling.

**Telephony adapter (a port, with one adapter per provider)**
- Outbound: the API asks the provider to connect the telecaller, signed in to the provider's mobile app, and the parent. The provider shows the centre's number to the parent.
- Inbound: the provider calls the API on each incoming call with the caller number and the dialled number. The API returns who to ring in under 500 ms. If it does not answer in time, the provider's own ring group takes the call.
- Events: call started, answered, ended and recording ready arrive by webhook. The API checks the sender (signature where the provider has one, otherwise a secret header and the provider's IP list), ignores duplicates by call id, and fetches any missed recording later by the provider's call record API.
- Three routing patterns exist across providers, and the adapter hides them from the rest of the system. (1) The provider asks our API per call (Tata Smartflo's API dialplan, MyOperator's CRM step). (2) Our server holds the live call and transfers it (Superfone). (3) The provider routes by its own rules and we copy assignments into the provider (MyOperator's sticky agent, a ring group).
- Port in plain terms: start an outbound call for a lead and an agent; decide an inbound call; read an event; fetch a recording; add, change or remove an agent. Section 7.6 lists what each provider documents.

**Desk endpoints (all behind sign-in, centre scope and audit)**
- Leads: list and search (masked), read, create, update, assign, merge duplicates, status change with reason, notes, follow-up tasks.
- Calls: `POST /admin/leads/{id}/call`, list calls for a lead, call summary and transcript, recording stream (roles with permission only), missed calls.
- Reveal: `POST /admin/leads/{id}/reveal-number` (super admin, fresh sign-in, reason).
- Review: flags list and decision, canary hits, access-pattern alerts, audit log search.
- Admin: users, roles, centres, routing rules, windows and limits, dashboards, data-rights export and delete.
- Live: a server connection per open desk page for the screen pop and task alerts.
- Webhooks in (one path per provider): call events, inbound routing question, recording ready.

**AI pipeline**
- A worker fetches the recording, sends it to the chosen speech engine, then to a language model with a fixed prompt that returns a summary and a list of flags as structured data.
- The misuse check combines the transcript flags (asking for another number or a WhatsApp number) with the access log patterns from FR-GUARD-7.
- Engines sit behind adapters so a better Marathi model can replace one by changing a setting. Where the engine runs is a data location decision recorded before launch.

**Screen pop**
- When the provider asks for routing, the API also pushes the lead card and last summaries to the chosen executive's open desk page over a server connection.

**Security**
- The Content Security Policy of the main site applies. The desk has its own policy file, same rules, with `connect-src` limited to its API.
- Secrets in a secret manager, least-privilege database roles, rate limits, the webhook signatures, a scan on every preview, and the dependency rules in `CLAUDE.md`.
- Everything a manager may change is data: pipeline statuses, routing rules, windows, limits, retention, working hours.

## 11. Pilot and decision gate

Before choosing the provider and the speech engine:
1. **Shortlist** Tata Smartflo, Exotel, MyOperator and Superfone, and ask Knowlarity and Ozonetel for quotes. Send each the checklist below. Tata Smartflo and Superfone are added because their developer docs are public, which makes the pilot quick.
2. **Collect 50 real Marathi and 50 real Hindi calls** (with consent), including mixed-language calls and noisy ones.
3. **Compare** Sarvam, the provider's own AI, and one more engine on word accuracy and on the usefulness of the summary, judged by two counsellors.
4. **Run a call test** with each shortlisted provider on a trial number. Test masked outbound, inbound routing by caller, sticky routing, webhook speed and recording access. Also test what happens when our API is down.
5. **Decide** and record it in an ADR, with the written quote.

Vendor checklist (ask in writing):
- Can the telecaller be connected to the parent without either seeing the other's number? Which API?
- Can our API decide per inbound call who rings, within 500 ms? What happens on a timeout?
- Is there a built-in sticky agent, with a time window and a strict mode?
- What number types and city codes can D-SAP get, and what is the registration process and time?
- Are recordings and call data kept in India? Can we pull recordings by API and delete them?
- Which languages does the speech and summary feature support, with a live demo on our calls?
- What are the per-minute rates by call type, the pulse length, the number rental, the seat price and the minimum commitment?
- Which model does the mobile app use: calling inside the app over the internet, or a call to the telecaller's phone number first? Which telecom licence does it rely on (section 6)?
- Can the desk start a call through the API so the telecaller never types or sees the parent's number? Does the app show the parent's number anywhere (call log, notifications, recent calls)? Can the dial pad and contacts be switched off for telecaller users?
- Does the parent see the institute's number, and never the telecaller's personal number?
- When an inbound call rings the telecaller's phone, what does the phone show, and what does the phone's call log keep? Test on Android and iPhone.
- Is a +91 22 or +91 20 number available to D-SAP, on which licence, and in how many days?
- Is the webhook signed? Are failed deliveries retried? Is there a call record API to fetch what was missed?
- Can the app and the recordings be switched off for a telecaller the same day they leave?
- What are the rate limits and the uptime commitment?

## 12. Risks

| Risk | Effect | Handling |
|---|---|---|
| A telecaller memorises or photographs numbers | Leads leave | Watermark, canaries, flags, no downloads, contracts and disciplinary rules |
| Provider cannot do per-call routing or masking as needed | Design change | Pilot before commitment; adapter keeps the choice open |
| Marathi speech quality is poor on phone audio | Wrong summaries | Pilot on real calls; human correction (FR-AI-6); a second engine |
| Telecom rules on number series or caller ID change | Calls blocked | Provider confirmation in writing; Phase 1 review; settings not code |
| Recording consent is not collected properly | Legal exposure | Notice on the form and by voice; Phase 1 wording |
| The build is larger than estimated | Delay | Release in stages: leads and RBAC first, then calling, then AI and guard features |
| Single developer dependence | Maintenance risk | Documentation in this repository; adapters and tests |
| Telecallers use personal phones, which D-SAP does not control | Screenshots or screen recording of the app; a leaver keeps the app | The desk and the app never show a real number; a written device policy; the app account is removed on the day of leaving; watermark and flags still apply |
| A new public number breaks the site's and the Google profile's phone details | Lost calls, mismatched business details | Move all of them in one planned change and keep the old number forwarding (section 6.1) |

## 13. Questions for D-SAP

Answered on 2026-11-02:
- The desk domain is `admin.dsapghule.com`, owned by D-SAP.
- Telecallers answer on their own mobile phones through the provider's app. A desk phone is possible if needed.
- No automated or recorded voice. A person always calls and receives. AI is for assistance and summaries.
- A new dedicated number is needed. The existing +91 22 6971 9828 is on Heyo, which has no call masking.
- Telecallers use Microsoft email. There are 2 to 3 telecallers per centre. The super admin reviews recordings and flags. The Heyo number stays. Telecallers use the provider's app on personal phones. The new number should be in the 22 or 20 series.

Still open:
1. How long should recordings and transcripts be kept?
2. What monthly running cost is acceptable?
3. Should the Heyo number forward to the new one, or stay as a separate line for the centre? (It stays in use. This decides what the website shows.)
4. Which city code for the new number (Pune 020 or Mumbai 022) if the provider offers a choice? Pune matches the centres.
5. Who covers for the super admin when they are away, so flags are not left unreviewed?
6. Who signs the written device policy, and what happens on a breach?

## 14. Sources (read 2026-11-02)

Vendor documentation:
- Exotel: [number masking setup](https://developer.exotel.com/docs/advanced-config/number-masking-setup), [Lead Assist API](https://developer.exotel.com/api/lead-assist), [click to call](https://developer.exotel.com/?p=4979)
- MyOperator: [call routing](https://myoperator.com/call-routing), [sticky agent](https://myoperator.com/sticky-agent), [counsellor-based routing with a CRM](https://support.myoperator.com/portal/en/kb/articles/how-do-i-integrate-myoperator-with-nopaperforms-merrito-telephony-apis-for-1-click-dial-inbound-pop-ups-and-counsellor-based-call-routing)
- Superfone developer docs: [getting started](https://docs.superfone.dev/docs/sfvopi/getting-started/), [click to call](https://docs.superfone.dev/docs/crm/click-to-call/), [call info](https://docs.superfone.dev/docs/api/call-info), [event notifications](https://docs.superfone.dev/docs/crm/event-notifications/)
- Tata Smartflo developer docs: [API dialplan](https://docs.smartflo.tatatelebusiness.com/docs/api-dialplan-use-cases), [click to call support API](https://docs.smartflo.tatatelebusiness.com/docs/click-to-call-support-api), [call records](https://docs.smartflo.tatatelebusiness.com/reference/v1callrecords.md)
- Knowlarity (third-party guides): [Salesmate click to call](https://support.salesmate.io/hc/en-us/articles/360018477352), [Meritto](https://help.meritto.com/portal/en/kb/articles/knowlarity-old-config)
- Interakt: [WhatsApp voice calling](https://www.interakt.shop/resource-center/whatsapp-voice-calling-on-interakt/)
- ElevenLabs: [phone number API](https://elevenlabs.io/docs/api-reference/phone-numbers/create.md), [Plivo guide for ElevenLabs in India](https://docs.plivo.com/docs/voice-agents/sip-trunking/integration-guides/elevenlabs)
- Microsoft: [Operator Connect for India](https://learn.microsoft.com/en-us/microsoftteams/operator-connect-india-plan), [PSTN options](https://learn.microsoft.com/en-us/microsoftteams/pstn-connectivity)
- Zoho Voice: [FAQ](https://help.zoho.com/portal/en/kb/zoho-voice/zoho-voice-faqs/articles/zoho-voice-frequently-asked-questions)
- Frappe CRM: [Exotel integration](https://docs.frappe.io/crm/exotel)
- Plivo: [India calling](https://www.plivo.com/docs/voice/concepts/india-calling)
- Superfone: [Play Store listing](https://play.google.com/store/apps/details?id=com.superfone&hl=en_IN), [site](https://www.superfone.in/), [SoftwareSuggest](https://www.softwaresuggest.com/superfone-business-number)
- Number masking vendors: [Acefone](https://www.acefone.com/solutions/number-masking/), [Edesy click to call](https://edesy.in/number-masking/click-to-call), [Fonada](https://fonada.com/number-masking)
- Twilio: [India voice guidelines](https://www.twilio.com/en-us/guidelines/in/voice)
- TRAI: [guidelines for principal entities, 18 June 2024](https://connectbroadband.in/cms/TRAI%20Guidelines%20for%20PEs%20-%2018%20June%202024.pdf) (a copy on a third-party site; confirm on trai.gov.in)

Third-party pricing and comparisons (less reliable):
- Exotel: [Techjockey](https://www.techjockey.com/detail/exotel-call-recording-software), [Dialnexa](https://dialnexa.com/blogs/exotel-pricing/), [Bonvoice](https://bonvoice.com/insights/exotel-pricing-vs-bonvoice/)
- Indian providers: [ITforSME cloud telephony cost](https://www.itforsme.in/pricing/cloud-telephony-cost-india), [FreJun MyOperator alternatives](https://frejun.com/myoperator-alternative/)
- LeadSquared: [Capterra](https://www.capterra.com/p/130199/LeadSquared/), [ITQlick](https://www.itqlick.com/leadsquared/pricing), [Salesvora coaching CRMs](https://salesvora.com/blog/best-crm-for-coaching-institutes-in-india)
- Zoho CRM: [Maxwize](https://maxwize.in/blog/zoho-crm-pricing-india), [ITforSME](https://www.itforsme.in/pricing/zoho-crm-india)
- Kylas: [Capterra](https://www.capterra.com/p/210630/Kylas/pricing/), [G2](https://g2.com/products/kylas-sales-crm/pricing)
- Sarvam AI: [Smallest.ai summary](https://smallest.ai/blog/sarvam-ai-speech-to-text-pricing), [MarkTechPost on Saaras V4](https://www.marktechpost.com/2026/09/26/sarvam-ai-releases-saaras-v4-a-speech-to-text-model-for-all-22-indian-languages-and-global-english/)
- Speech accuracy claims: [Gnani glossary](https://www.gnani.ai/resources/blogs/blog-speech-to-text-glossary-asr-terminology), [ConvoZen Marathi](https://convozen.ai/products/speech-to-text-marathi), [Convin speech to text](https://convin.ai/speech-to-text)
- Teams: [AVOXI India guide](https://www.avoxi.com/solutions/sip-integration/microsoft-teams-direct-routing/india/), [AeroCom](https://www.aerocominc.com/info/?p=11427), [UC Today](https://www.uctoday.com/unified-communications/how-much-is-operator-connect/)
- India telecom rules: [Ozonetel VoIP in India](https://ozonetel.com/voip-in-india/), [TCCCPR third amendment dates](https://www.thetelephony.co/india/blog/tcccpr-third-amendment-dates), [Bonvoice TRAI compliance](https://bonvoice.com/insights/trai-compliance/)
