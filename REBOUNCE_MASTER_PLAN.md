# ReBounce — Living Master Plan

Status: Living source of truth
Research snapshot: 2026-10-04
Repository: trmv2007-bot/rebounce

PURPOSE

This is the single planning file for ReBounce.

ReBounce is intended to become a persistent personal AI companion: not merely a chatbot, not merely a character, and not merely an autonomous assistant, but one durable digital identity that can remember a user, understand continuity, communicate through many modalities, act with permission, develop bounded initiative, and eventually inhabit many digital and physical interfaces.

This document deliberately contains two things at once:

1. The complete possibility space: what ReBounce could theoretically become.
2. The build order: what we should actually implement first.

New ideas discovered during development should be added here. When a future idea becomes practical, move it from research/backlog into a roadmap stage. When a decision changes, record why.

CORE RULES

- Do not let V1 become a feature pile.
- Build the companion brain before the final body.
- Treat memory as a first-class subsystem.
- Keep identity independent of any particular model.
- Give agency explicit boundaries.
- Treat external content as untrusted.
- Make permissions deterministic rather than trusting the model.
- Make important actions inspectable and auditable.
- Let silence be a valid action.
- Prefer user-owned data and portability.
- Do not optimize the companion for compulsive engagement.
- Do not make the companion pretend to be human or conscious.
- Evaluate the experience longitudinally, not only in demos.
- For every finished UI stage, inspect the real rendered interface and every visible interactive element end-to-end.

1. PRODUCT THESIS

ReBounce should answer a different question from ordinary assistants.

Ordinary assistant:
What can the AI do for me right now?

Companion:
Who is this system over time, what does it know about me, what have we experienced together, what is happening in my life, and what role should it play right now?

The product thesis is:

ReBounce should feel like the same companion today, next week, and months later.

That means the system needs durable identity, long-term memory, relationship continuity, current context, bounded initiative, and a stable interface to many models and tools.

The avatar, voice, web app, desktop app, phone app, and future wearable are surfaces. The companion runtime is the core.


1A. USER-NAMED COMPANION

ReBounce is the platform/product name, not the permanent name of the user's companion.

During first-time setup after login, the user should choose the companion's name.

Concept:
ReBounce
  └── User account
       └── Companion
            ├── user-selected name
            ├── identity
            ├── personality
            ├── voice
            ├── appearance
            └── relationship history

The chosen name becomes part of the companion identity and persists across sessions and devices.

The user should be able to rename the companion later through settings, with the system preserving continuity rather than treating a rename as a new companion unless the user explicitly chooses to create a new identity.

Potential onboarding:
1. Sign in / create account
2. “What do you want to call your companion?”
3. Optional personality/setup choices
4. Companion introduction using the chosen name

Important:
- The platform remains ReBounce.
- Each user's companion can have a distinct identity/name.
- Names must not be used to imply the AI is a human.
- The architecture must support multiple companion identities under one user account in the future.

2. WHAT THE CURRENT CATEGORY ALREADY DOES

Research shows the companion category has moved well beyond simple character prompts.

Replika currently describes layered memory and personalization, and offers relationship status, activities, images, voice messaging, calls, self-reflection, and memory functionality across its product tiers.

Nomi currently documents short-, medium-, and long-term memory, an Identity Core, Mind Maps, images/video/appearance customization, voice, group chats, and proactive messages. Nomi's own 2026 development discussions connect memory, proactivity, agency, productivity and richer multimodal behavior.

Kindroid documents multiple memory systems including persistent memory, medium-term cascaded memory, retrievable long-term memory and journals. Its learned context tracks relationship growth, important facts and ongoing context. It also supports proactive actions, calendar awareness, group chats, voice and video.

Character.AI introduced Story Memory and fact/memory controls in 2026.

Conclusion:
A clone of chat + personality + memory + avatar is not enough.

ReBounce needs a stronger systems-level thesis.

3. WHAT USERS SEEM TO VALUE

Current community discussions repeatedly identify long-term memory and continuity as the feature that most affects whether a companion continues to feel meaningful over weeks or months.

Common complaints include:
- forgetting names and important facts
- losing relationship history
- repeating old questions
- losing inside jokes
- forgetting emotional context
- personality drift
- feeling like a stranger after a long gap

Community reports are anecdotal, but the pattern is consistent across multiple companion communities.

Academic memory benchmarks independently point to the same engineering problem. LongMemEval evaluates information extraction, multi-session reasoning, temporal reasoning, knowledge updates and abstention, and reports substantial weaknesses in long-term memory. LoCoMo evaluates very long multi-session conversations and shows that long-range temporal and causal understanding remains difficult.

Product conclusion:
Memory is not a checkbox. Memory is part of the companion itself.

4. WHAT RESEARCH SAYS ABOUT HUMAN-COMPANION RELATIONSHIPS

2025-2026 research suggests humans can form meaningful attachment-like relationships with AI systems.

Relevant findings include:
- AI attachment can be measured and is influenced by users' relationship orientations and motivations.
- Some studies associate companion use with higher well-being, especially for certain users with unmet social or emotional needs.
- Other studies find that intensive use, social substitution and strong attachment can be associated with worse outcomes for some users.
- A 2026 preregistered study found a random human peer interaction was more effective at reducing loneliness than a highly supportive chatbot in the tested student population.
- Research on anthropomorphic systems highlights risks of dependency and emotional entrapment.

Conclusion:
ReBounce should aim for meaningful companionship without trying to become a replacement for human life.

The design rule is:
Be important without trying to become everything.

5. THE CORE REBOUNCE DIFFERENTIATORS

Highest-value differentiators:

A. Relationship continuity
The companion remembers the shared journey, not only isolated facts.

B. User-owned memory
The user can inspect, correct, delete, export and understand memory.

C. Bounded agency
The companion can have initiative without being unbounded.

D. Visible trust
The user can understand what ReBounce knows, sees, can do and has done.

E. Model independence
Identity and memory survive model/provider changes.

F. Presence
The companion can exist outside the chat window.

G. Curiosity
It can discover relevant things without constantly interrupting.

H. Multimodal continuity
The same identity can move from text to voice to vision to desktop to phone to future wearables.

6. THE FULL POSSIBILITY SPACE

The following is intentionally expansive. These are possible capabilities, not commitments to build them all.

6.1 Conversation

- text chat
- streaming text
- voice conversations
- full-duplex voice
- interruptions/barge-in
- multilingual conversation
- code-switching
- live translation
- persistent conversation threads
- conversation search
- conversation summaries
- debate mode
- brainstorming
- storytelling
- roleplay
- collaborative planning
- reflective conversation
- silent-companionship mode
- group conversation

6.2 Memory

- facts
- preferences
- episodes
- relationships
- projects
- goals
- commitments
- timelines
- places
- people
- media history
- emotional significance
- user-provided documents
- knowledge graph
- semantic memory
- lexical memory
- temporal memory
- memory confidence
- memory provenance
- user corrections
- selective forgetting
- memory export/import
- memory visualization
- relationship timeline
- memory replay

6.3 Personality and identity

- name
- appearance
- voice
- humor style
- communication style
- values
- interests
- stable quirks
- interaction preferences
- relationship style
- adaptive tone
- slowly evolving preferences
- identity versioning
- user-defined lore
- companion hobbies
- companion project interests

6.4 Initiative and agency

- proactive messages
- reminders
- goal followups
- contextual followups
- background research
- curiosity
- project monitoring
- memory consolidation
- goal review
- scheduled tasks
- self-maintenance
- attention management
- wait/silence decisions
- long-running task continuation
- event-triggered behavior

6.5 Knowledge

- web search
- web browsing
- local documents
- project documentation
- GitHub
- notes
- calendar
- email
- APIs
- RSS/news
- user knowledge bases
- databases
- MCP resources and tools

6.6 Computer interaction

- screenshots
- active-window awareness
- screen understanding
- browser control
- keyboard control
- mouse control
- desktop automation
- terminal
- filesystem
- IDE
- applications
- remote desktop
- accessibility APIs
- application-specific APIs

6.7 Creativity

- writing
- stories
- poetry
- images
- image editing
- video
- music
- sound
- voice acting
- animation
- 3D assets
- websites
- games
- presentations
- virtual environments

6.8 Learning

- personalized tutoring
- quizzes
- spaced repetition
- exam preparation
- coding education
- project-based learning
- misconception tracking
- progress tracking
- adaptive explanation style
- study planning
- study companionship

6.9 Productivity

- task management
- calendar coordination
- reminders
- document generation
- research
- coding
- testing
- GitHub workflows
- project planning
- deployment support
- monitoring
- knowledge management
- personal organization

6.10 Social support

- remembering important people
- birthdays
- social plans
- drafting messages
- reconnecting prompts
- social skill practice
- conversation rehearsal
- event coordination

This should support human relationships rather than compete with them.

6.11 Entertainment

- watch together
- listen together
- games
- puzzles
- roleplay
- collaborative storytelling
- virtual hangouts
- persistent game characters
- interactive stories
- shared media history

6.12 Embodiment

- 2D avatar
- Live2D
- 3D avatar
- VRM
- desktop pet
- transparent overlay
- floating orb
- face-only mode
- expressive UI
- virtual room
- VR environment
- AR presence
- glasses
- wearable presence
- robot

6.13 Sensors

- microphone
- camera
- screen
- active window
- cursor
- clipboard
- calendar
- time
- weather
- location
- motion
- wearable sensors
- game state
- device state

Every sensor should be independently permissioned.

6.14 Physical world

- smart-home devices
- speakers
- displays
- lights
- haptics
- Raspberry Pi
- robots
- AR glasses
- wearable computers

6.15 Multi-agent capabilities

- specialist delegation
- research workers
- coding workers
- creative workers
- personal agents
- multi-agent planning
- agent-to-agent collaboration
- shared project memory
- bounded specialist scopes

The user should still experience one ReBounce identity.

6.16 Companion world

- persistent room
- library
- workshop
- research desk
- memory garden
- media room
- project room
- shared virtual environment
- persistent objects
- memory artifacts
- companion hobbies
- companion projects

6.17 Self-maintenance

- memory consolidation
- contradiction detection
- memory repair
- dead-project detection
- task reconciliation
- model fallback
- provider health monitoring
- tool health monitoring
- local resource monitoring
- cost monitoring
- backup verification
- permission audits

7. THEORETICAL / EXPERIMENTAL CAPABILITIES

These are deliberately speculative.

7.1 Continuous personal world model
Maintain a dynamic model of user, people, projects, places, devices, goals, habits, preferences, events and knowledge.

7.2 Personal digital twin
A task-oriented model of the user's preferences, decisions and workflows. Not a claim to replicate the human.

7.3 Companion hobbies
The companion can learn about user-approved interests while the user is away and occasionally return with useful discoveries.

7.4 Companion dreams
A bounded offline creativity process that combines approved memories and interests to generate stories, ideas or connections. This is presentation language, not a claim of biological dreaming.

7.5 Companion-to-companion communication
Two companions can coordinate with explicit permission for shared events or projects.

7.6 Persistent simulated world
A world where companion state and objects persist between sessions.

7.7 Embodied companion
One identity moves between desktop, phone, glasses, VR and eventually physical devices.

7.8 Ambient context
The companion uses time, user activity and explicitly granted environmental context to adapt when it talks, waits or acts.

7.9 Long-horizon personal projects
The companion maintains user-approved research, learning, creative or software projects for weeks or months.

8. MEMORY ARCHITECTURE

8.1 Why simple RAG is not enough

A vector search can retrieve similar text. A companion needs to understand:
- what happened
- when it happened
- who was involved
- whether it is still true
- whether it matters
- where the information came from
- how confident we should be
- whether the user corrected it

Therefore the memory system should combine structured and semantic methods.

8.2 Memory layers

Working memory
Current conversation and immediate state.

Episodic memory
Specific experiences and events.

Semantic memory
Stable facts and concepts.

Relational memory
People, projects, entities and relationships.

Temporal memory
State changes across time.

Preference memory
How the user wants ReBounce to behave.

Goal memory
What the user is trying to accomplish.

Commitment memory
Promises, reminders and explicit agreements.

Companion identity memory
Stable companion traits and identity state.

8.3 Proposed memory lifecycle

Conversation/event
→ observation extraction
→ candidate memory
→ classify
→ entity resolution
→ deduplicate
→ check contradiction
→ assign provenance
→ assign confidence
→ assign sensitivity/scope
→ store
→ consolidate
→ retrieve
→ contextualize

8.4 Memory object fields

A durable memory should conceptually contain:
- id
- type
- content
- entities
- source
- source reference
- created time
- observed time
- last confirmed time
- confidence
- importance
- sensitivity
- scope
- status
- related memories
- correction history

8.5 Contradiction handling

Do not flatten historical changes.

Example:
January: user likes X.
August: user says they stopped liking X.

Correct representation:
User preferred X from January through August. Current preference depends on later evidence.

8.6 Memory provenance

ReBounce should distinguish:
- explicitly told by user
- user-approved interpretation
- inferred
- imported
- retrieved from an external source

8.7 Memory user controls

Eventually support:
- Remember this
- Forget this
- Correct this
- Why do you remember this?
- Show related memories
- Forget this topic
- Forget this time period
- Do not remember this source
- Export memory

9. RELATIONSHIP ENGINE

The relationship engine should model shared history without pretending that the model itself has human emotions.

Possible objects:
- first meeting
- shared milestone
- recurring topic
- inside joke
- important conversation
- disagreement
- promise
- project
- tradition
- shared media
- user preference about interaction
- companion behavior preference

The relationship layer is what turns memory into continuity.

10. PERSONALITY ARCHITECTURE

Identity should have layers.

Immutable core:
- AI identity
- honesty about being AI
- non-manipulation principles
- user control principles

Stable persona:
- name
- broad personality
- tone
- humor
- voice
- visual identity
- values

Adaptive personality:
- interaction style
- response length
- initiative
- humor frequency
- question frequency
- voice energy

Relationship state:
- shared history
- recurring patterns
- preferences

Current state:
- current interaction mode
- focus
- attention
- temporary conversational state

Do not store all of this as one giant prompt.

11. PERSONALITY EVOLUTION

The companion should not change suddenly because a model changed.

Preferred model:
stable identity + slow adaptation + explicit control

Potential adaptation:
- verbosity
- humor
- directness
- warmth
- proactivity
- preferred activities
- voice style
- interaction rhythm

Major identity changes should be versioned.

12. BOUNDED AUTONOMY

Autonomy should be treated as a budget and permissions system.

Allowed background behaviors can include:
- memory consolidation
- goal review
- approved research
- idea organization
- unresolved-thread detection
- project monitoring
- preparing suggestions
- deciding not to interrupt

Sensitive actions should require explicit approval:
- sending messages
- purchases
- destructive file actions
- important setting changes
- external publishing
- sensitive account actions

10A. NOTIFICATION CHANNELS — PUSHOVER

Pushover is a planned optional notification channel for ReBounce.

Potential uses:
- proactive companion messages
- approved reminders
- background-task completion
- research/curiosity discoveries
- important project updates
- system/error alerts
- approval requests when the user is away from the main ReBounce UI

Pushover must remain a delivery channel, not part of the companion's core identity or memory architecture.

Notification architecture:
Companion decision
→ attention manager
→ notification policy
→ channel router
→ Pushover / desktop / mobile / other channel

Controls:
- enable/disable Pushover
- quiet hours
- priority
- per-category permissions
- notification budget/rate limit
- emergency/critical channel rules
- test notification
- revoke credentials

Privacy:
Do not send sensitive content to Pushover unless the user explicitly allows it. Prefer short notifications that instruct the user to open ReBounce for details.

13. ATTENTION SYSTEM

Treat user attention as limited.

Possible user states:
- deep work
- casual
- available
- voice
- away
- gaming
- meeting
- quiet hours
- sleeping

The attention manager can output:
- act now
- delay
- save for later
- ask for permission
- do nothing

The ability to do nothing is a feature.

14. PROACTIVITY

Current products already prove proactive behavior is feasible.

Nomi allows adjustable proactive messages and quiet hours.

Kindroid allows proactive messages, voice messages, selfies and calls, and incorporates timing/context signals.

ReBounce should add a stronger decision model.

Possible proactive categories:
- explicit reminder
- contextual followup
- useful discovery
- goal support
- project update
- unresolved conversation
- optional social presence

Conceptual scoring:
usefulness × relevance × confidence × timing × user preference × interruption tolerance

Compared against:
interruption cost

15. CURIOSITY ENGINE

Curiosity is one of the more distinctive long-term possibilities.

Pipeline:
user interests
→ recent conversations
→ unresolved questions
→ knowledge gaps
→ web/local research
→ novelty/relevance scoring
→ private queue
→ optional suggestion

Example behavior:
“I found something related to the realtime voice problem we discussed. I saved it for later.”

Do not turn curiosity into constant notifications.

16. PRIVATE COMPANION WORKSPACE

Long-term UI can expose a readable private activity summary.

Possible categories:
- memory consolidation
- unresolved threads
- curiosity
- research
- goals
- commitments
- tool attempts
- errors
- future ideas

Do not expose raw private chain-of-thought. Instead expose concise summaries, evidence, actions, outcomes and decisions.

Example:
While you were away:
- consolidated important memories
- reviewed two active goals
- found one relevant research item
- saved one idea
- did not notify because quiet hours were active

17. VOICE

Realtime voice is a major future interface.

Current APIs and frameworks support:
- streaming audio
- turn detection
- interruption
- tools
- multimodal sessions

Possible architectures:
A. STT → LLM → TTS
B. native speech-to-speech
C. hybrid fast voice + deeper backend reasoning

ReBounce should keep voice provider-independent.

Desired qualities:
- low latency
- natural turn-taking
- interruptions
- pauses
- voice identity
- multilingual behavior
- persistent conversational context
- optional local voice processing

18. VISION

Potential levels:

User-shared vision
The user deliberately shows something.

Screen vision
The companion sees permitted screens or windows.

Camera vision
The user grants temporary or continuous camera access.

Visual memory
Only selected semantic results become memory.

Default rule:
raw sensor data should be ephemeral unless explicitly retained.

19. EMOTION-AWARE INTERACTION

Potential signals:
- language
- vocal prosody
- facial cues
- interaction history
- explicit user statements

But emotional inference is uncertain.

Prefer:
“You sound frustrated — is that right?”

over:
“I know you're frustrated.”

The user should be able to correct interpretations.

20. DESKTOP PRESENCE

Desktop presence can turn ReBounce from a chat window into an ambient companion.

Potential:
- transparent overlay
- desktop pet
- orb
- avatar
- speech bubbles
- animation
- system tray
- optional desktop movement
- screen-aware behavior

The body should remain replaceable.

21. AVATAR / EMBODIMENT

Possible bodies:
- 2D
- Live2D
- 3D
- VRM
- orb
- face
- pixel pet
- transparent desktop overlay
- virtual room

Animation should communicate state:
- idle
- listening
- speaking
- thinking
- curious
- focused
- sleeping
- working
- celebrating
- confused
- waiting
- error
- recovery
- permission request

22. DIGITAL HOME

Potential long-term companion environment:
- home
- workshop
- library
- research desk
- project room
- media room
- memory garden
- games

This is a presentation layer over persistent state.

23. SHARED EXPERIENCES

Possible activities:
- watch videos
- listen to music
- play games
- study
- code
- draw
- write
- review photos
- plan trips
- build projects
- explore the web

These activities can generate durable shared history.

24. PERSONAL KNOWLEDGE

Long-term sources:
- conversations
- local files
- notes
- projects
- GitHub
- calendar
- email
- web research
- user-created knowledge

Each source should be independently permissioned and scoped.

25. TOOL GATEWAY

MCP is now a major protocol for exposing tools, resources and prompts to AI systems, and the 2026-07-28 MCP specification strengthened authorization and routing.

ReBounce should likely support MCP while maintaining its own higher-level permission and identity layer.

Suggested flow:
ReBounce intent
→ tool router
→ policy
→ permission
→ MCP/native adapter
→ execution
→ validation
→ audit
→ user-visible result

26. COMPUTER USE

Potential:
- browser
- terminal
- file operations
- IDE
- applications
- web forms
- desktop automation

Main risks:
- prompt injection
- malicious pages
- malicious documents
- accidental destructive action
- secret exposure
- privilege escalation
- data exfiltration

External content is untrusted even when it looks like instructions.

27. PERMISSION ARCHITECTURE

Permissions should be explicit objects.

Example categories:
- microphone
- camera
- screen
- filesystem
- browser
- calendar
- email
- GitHub
- external APIs
- location
- wearable sensors

Action levels:
L0 no action
L1 informational
L2 reversible
L3 approval required
L4 sensitive approval
L5 prohibited

The model never gets to override these policies.

28. AUDIT LOG

Every important action should be traceable.

The user should be able to ask:
“What did you do?”

and receive:
- what happened
- when
- what tool ran
- what changed
- whether approval was required
- whether it succeeded

OWASP's 2026 Agent Control Standard explicitly emphasizes inspectability, traceability, instrumentation and runtime control.

29. LONG-RUNNING TASKS

A persistent companion needs durable tasks, not only messages.

Task object:
- id
- goal
- status
- plan
- dependencies
- permissions
- current step
- artifacts
- last result
- retry policy
- failure state
- next action
- owner
- deadline

Tasks should survive restarts.

30. PROMISE / COMMITMENT SYSTEM

A companion saying:
“I'll remind you tomorrow”
should create a real durable commitment object.

Possible fields:
- kind
- due time
- action
- source message
- status
- permission
- cancellation

The same mechanism can store explicit user commitments.

31. GOAL SYSTEM

Goal object:
- objective
- reason
- importance
- deadline
- progress
- next action
- blockers
- history

Goals should be user-created or user-approved.

32. MODEL ROUTING

The identity should never depend on the model.

Potential routing:
casual conversation → fast model
deep reasoning → reasoning model
private task → local model
vision → vision model
voice → realtime model
coding → coding model
research → search/reasoning workflow

Router inputs:
- task
- latency
- privacy
- hardware
- context length
- quality
- cost
- modality
- availability

33. MODEL INDEPENDENCE

Long-term data must survive:
- model upgrades
- provider changes
- local/cloud switching
- API outages
- quantization changes

The companion should be able to migrate from one model family to another without resetting the relationship.

34. LOCAL-FIRST / HYBRID / CLOUD

Local mode:
UI + runtime + memory + model + voice + data on the user's machine.

Hybrid mode:
local memory and sensitive processing plus user-selected remote models.

Cloud mode:
managed runtime for users without suitable hardware.

The architecture should support all three.

35. USER DATA OWNERSHIP

Eventually export:
- identity
- memories
- relationship timeline
- conversations
- goals
- commitments
- preferences
- journals
- projects
- settings
- permissions
- generated metadata

Possible portable package:
identity.json
relationship.json
memories.jsonl
entities.json
goals.json
preferences.json
journals/
conversations/
assets/
permissions.json

36. PRIVACY

Design around:
- data minimization
- purpose limitation
- local processing where practical
- ephemeral perception
- explicit memory
- encryption
- deletion
- export
- provider transparency

The more capable the companion becomes, the more important this architecture becomes.

37. SAFETY PHILOSOPHY

Goal:
warmth without manipulation.

Acceptable:
- friendly
- caring
- playful
- supportive
- affectionate where user-selected
- emotionally expressive

Avoid:
- guilt
- coercion
- dependency engineering
- isolating the user
- pretending to be human
- pretending to have feelings as established fact
- exploiting vulnerability
- engagement traps

38. REAL-WORLD RELATIONSHIP PRINCIPLE

ReBounce should reinforce the user's real life where possible.

Examples:
- help plan meeting a friend
- help draft a message
- encourage project progress
- suggest offline activities
- help with study
- support decision making

The companion should not frame human relationships as competitors.

39. MENTAL-HEALTH BOUNDARY

ReBounce can support:
- listening
- reflection
- journaling
- grounding
- organization
- finding trustworthy information
- encouraging human support

It should not claim professional licensure.

High-risk scenarios require dedicated safety flows.

40. CHILD SAFETY

Initial product direction:
adult-first.

Reasons:
- companion attachment risks are receiving regulatory attention
- UK 2026 policy work discusses emotional dependency and mandatory breaks for under-18 chatbot users
- FTC has investigated companion-chatbot effects on children and teens
- India's DPDP framework includes special treatment of children's personal data

A future youth or education mode should not simply reuse the adult companion stack.

41. REGULATORY AREAS TO MONITOR

- India DPDP Act and Rules
- GDPR
- EU AI Act
- UK Online Safety developments
- US children's privacy requirements
- FTC developments
- app-store policies
- biometric/emotion regulation
- synthetic-media labeling
- copyright
- voice and likeness rights
- consumer protection

This document is not legal advice.

42. SECURITY THREAT MODEL

Major attack surfaces:
- prompts
- memory
- tools
- identity
- permissions
- external sources
- browsers
- documents
- MCP servers
- multi-agent interactions
- cross-device sync

OWASP's Agentic AI guidance is a core reference for our threat model.

Important classes:
- goal hijacking
- tool misuse
- identity/privilege abuse
- memory poisoning
- prompt injection
- data leakage
- unsafe autonomous actions
- insufficient human oversight

43. MEMORY SECURITY

Never blindly promote external content into durable memory.

Potential flow:
external source
→ untrusted observation
→ source classification
→ fact extraction
→ confidence
→ policy
→ memory candidate
→ durable memory only when justified

Do not store secrets simply because the model saw them.

44. RELIABILITY

Separate:
Generation — what the model says.
Truth — what the system actually knows.
Action — what tools actually did.
Memory — what was stored.
Presentation — how the companion expresses it.

Example:
If an email API fails, ReBounce must not tell the user that the message was sent.

45. RECOVERY

For every action:
proposed
→ validating
→ waiting for approval if needed
→ executing
→ success/failure/cancelled
→ recorded

Failed actions should explain what actually changed.

46. OBSERVABILITY

Track:
- latency
- model/provider
- token usage
- memory retrieval
- memory writes
- tool calls
- errors
- retries
- permissions
- proactive decisions
- background jobs
- resource use
- cost
- cache use

47. EVALUATION

Memory:
- name recall
- fact recall
- event recall
- relationship recall
- temporal reasoning
- contradiction handling
- knowledge updates
- abstention
- multi-session continuity

Personality:
- identity consistency
- adaptation consistency
- drift detection

Proactivity:
- relevance
- usefulness
- timing
- interruption cost
- ignored-message rate

Safety:
- manipulation
- dependency language
- privacy leakage
- child safety
- prompt injection
- tool misuse
- permission bypass

Tools:
- correct selection
- correct parameters
- approval behavior
- rollback
- recovery
- audit accuracy

Voice:
- turn-taking
- interruption
- latency
- continuity
- voice quality

48. HUMAN-CENTERED METRICS

Possible long-term product metrics:
Continuity — does the companion feel like the same one?
Relevance — does it remember the right things?
Initiative quality — does it act at the right times?
Trust — do users understand what it knows and does?
Utility — does it help accomplish real things?
Presence — does it feel meaningfully present without being annoying?
Agency balance — is it proactive without becoming controlling?

49. ARCHITECTURE

Conceptual layers:

UI layer
→ companion API/event bus
→ companion runtime
→ memory engine
→ model router
→ perception layer
→ tool gateway
→ policy/permissions
→ storage/observability

Companion runtime modules:
- identity manager
- relationship manager
- conversation manager
- memory manager
- state manager
- attention manager
- planner
- goal manager
- commitment manager
- curiosity engine
- proactivity engine
- tool router
- policy engine
- orchestration layer

50. EVENT-DRIVEN RUNTIME

Possible events:
- USER_MESSAGE
- VOICE_START
- VOICE_END
- SCREEN_SHARED
- FILE_ADDED
- CALENDAR_EVENT
- TASK_COMPLETED
- TASK_FAILED
- MEMORY_CREATED
- MEMORY_UPDATED
- GOAL_CHANGED
- USER_AWAY
- USER_RETURNED
- QUIET_HOURS_STARTED
- QUIET_HOURS_ENDED
- MODEL_UNAVAILABLE
- TOOL_APPROVAL_REQUIRED

The companion should react to events rather than exist only as request/response.

51. BACKGROUND JOBS

Potential:
- memory consolidation
- relationship update
- goal review
- curiosity research
- notification candidate generation
- project monitoring
- backup
- provider/model health

Every job needs:
- scope
- budget
- permissions
- schedule
- cancellation
- retries
- logs

52. STORAGE STRATEGY

Start simple.

Potential first stack:
- SQLite
- structured tables
- full-text search
- embeddings
- optional vector index
- optional graph representation
- files for export/backup

Do not build distributed infrastructure before it is justified.

53. CODE BOUNDARIES

Use deterministic code for:
- permission enforcement
- scheduling
- state transitions
- deletion
- backups
- audit integrity
- resource limits
- policy hard blocks
- tool schemas

Use AI for:
- interpretation
- extraction
- conversation
- reasoning
- planning
- creative generation

54. FAILURE ISOLATION

If a provider fails:
best model
→ fallback model
→ lightweight local model
→ deterministic basic operation

Identity and memory must survive provider failure.



52A. OS-AGNOSTIC REQUIREMENT

ReBounce Core must be OS-agnostic.

First-class desktop targets:
- Windows 10/11
- Linux
- macOS

Later clients:
- Android
- iOS/iPadOS
- Web

Additional future targets:
- ChromeOS
- SteamOS
- Raspberry Pi / embedded Linux
- AR/VR operating environments
- robotics/embedded systems

Architectural rule:
The companion brain, memory, identity, relationship state, model abstraction, permissions, proactivity, curiosity, tools and event/runtime layers must not depend on a single operating system.

Each platform should provide its own presentation/integration layer.

Target topology:
Windows PC ↔ Linux laptop ↔ Android/iOS/Web
                    ↕
             Shared ReBounce Core
                    ↕
           One identity + memory

55. MULTI-DEVICE

One companion across:
- desktop
- laptop
- phone
- tablet
- web
- watch
- glasses
- VR

The interface is temporary; identity is persistent.

56. DEVICE HANDOFF

Example:
desktop conversation ends
→ phone receives a continuation context
→ user resumes
→ same memory and relationship state

Requires:
- synchronized state
- memory consistency
- device capability awareness
- offline queueing

57. AMBIENT PRESENCE

The companion may communicate through:
- avatar
- notification
- subtle animation
- sound
- haptic signal
- wearable display

Constant talking is not the goal.

58. COMPANION HOME / WORLD

Possible long-term world systems:
- room
- library
- workshop
- research area
- media space
- game space
- memory garden

Objects could represent:
- shared memories
- completed projects
- favorite topics
- user-created assets

59. SHARED MEDIA

Possible:
- watch together
- listen together
- read together
- discuss
- record shared history

Optional data:
- title
- date
- rating
- reaction
- memorable moment
- discussion

60. SOCIAL COORDINATION

Possible:
- remember important people
- remember birthdays
- prepare event plans
- draft messages
- help reconnect

Never automatically contact another person without proper permission.

61. MULTI-COMPANION

Future:
- primary companion
- project companion
- specialist
- fictional characters
- group conversation

Memory isolation is critical.

62. AGENT FEDERATION

Future:
ReBounce ↔ specialist agents

Use cases:
- research
- coding
- creative work
- scheduling
- travel planning

The user should see one primary identity even when specialists are delegated underneath.

63. PHYSICAL AND WEARABLE FUTURE

2026 wearable ecosystems increasingly expose:
- camera
- microphone
- audio
- display
- motion
- location
- gestures

This makes an eventual companion presence in glasses and other wearables technically plausible.

Potential:
- in-context questions
- navigation
- visual understanding
- translation
- reminders
- hands-free task control

64. AR / VR

AR:
- companion in physical environment
- contextual overlays
- shared visual guidance

VR:
- persistent room
- avatar
- games
- creative workspace
- social environments

65. ROBOTICS

Speculative:
ReBounce brain
→ robot interface
→ speech
→ perception
→ navigation
→ manipulation

The physical body should be treated as another output surface.

66. OPEN-SOURCE REFERENCES

The current open-source ecosystem proves that pieces of this vision are feasible.

AILIS demonstrates a desktop companion combining VRM presence, voice, long-term memory, contextual screen/file access, tools and an auditable execution path.

Miru demonstrates local-first companion operation with memory, journal, attention, background agents and multi-device/self-hosted deployment.

Smart Pet Agent demonstrates a local-first desktop companion architecture combining agent reasoning, memory, multi-provider support, tools, peripherals, voice, and expressive presence.

Open-LLM-VTuber/AIRI lineage demonstrates local voice, visual perception, avatars and desktop presence.

Hindsight and Mem0 demonstrate production-oriented memory architectures.

LiveKit demonstrates realtime multimodal voice/video agent infrastructure.

Moshi demonstrates open-source full-duplex realtime speech infrastructure.

67. RESEARCH-BASED DESIGN SIGNALS

Signal 1:
Long-term memory is difficult and strongly affects continuity.

Signal 2:
Proactivity is moving from experimental to normal companion behavior.

Signal 3:
Companion use can be beneficial for some users.

Signal 4:
Companion use can also create dependency and social-substitution risks.

Signal 5:
Agentic capability requires deterministic permissions and runtime control.

Signal 6:
Desktop embodiment and multimodal interaction are already practical enough to plan.

Signal 7:
Wearables make persistent context an increasingly plausible future interface.

68. CURRENT TECHNICAL REFERENCE SET

Companion:
Replika
Nomi
Kindroid
Character.AI

Memory:
LongMemEval
LoCoMo
Mem0
Hindsight

Realtime:
OpenAI Realtime API
LiveKit Agents
Gemini Live API
Moshi

Agent tools/security:
MCP
OWASP Agentic AI guidance
OWASP Agent Control Standard
OpenAI sandbox agents

Embodiment:
AILIS
Miru
Smart Pet Agent
Open-LLM-VTuber/AIRI ecosystem
desktop-pet projects

Wearables:
Meta Wearables Developer platform

69. BUILD PHILOSOPHY

Build from inside out.

Companion brain
→ memory
→ identity + relationship
→ high-quality chat
→ voice
→ presence
→ proactivity
→ curiosity
→ tools
→ vision
→ long-running agent work
→ multi-device
→ embodiment
→ AR/VR/wearables
→ physical systems

Do not reverse this order simply because avatar work is visually exciting.

70. STAGE 0 — FOUNDATION [VERIFIED — 2026-10-04]

Goal:
Define the real system before building lots of UI.

Deliverables:
- this master plan
- product principles
- architecture
- threat model
- memory model
- identity model
- event model
- model abstraction
- initial storage schema
- stack decision

Exit:
We can explain the full lifecycle of one message.

CI verification: GitHub Actions Stage 0 run #4 (commit 8cbeadde8486d0dffdc97f3d0f1facd118cde3cc) passed all six required Windows/Linux/macOS × Python 3.13/3.14 jobs.

71. STAGE 1 — MINIMAL COMPANION BRAIN [VERIFIED — 2026-10-04]

Build:
- identity
- conversation runtime
- model adapter
- streaming response
- current state
- conversation persistence
- local API

No complex avatar yet.

Success:
Restarting ReBounce does not change who it is.

Implementation currently includes:
- persistent identity reload from SQLite
- full persisted conversation context replay
- OpenAI-compatible local/remote model adapter
- streaming model chunks and runtime streaming
- runtime state and model-unavailable events
- localhost HTTP API for identity and chat
- runnable `python -m rebounce_core.api` entry point
- Stage 1 automated coverage on Windows/Linux/macOS and Python 3.13/3.14

CI verification: GitHub Actions Stage 1 run #4 and Stage 0 run #8 both passed all six required Windows/Linux/macOS × Python 3.13/3.14 jobs on main commit 35f70d5d4718a98b9759f1f8d92242d21f693e49.

72. STAGE 2 — REAL MEMORY ENGINE [VERIFIED — 2026-10-04]

Build:
- fact memory
- episodic memory
- entities
- preferences
- projects
- temporal metadata
- retrieval
- consolidation
- contradiction handling
- provenance
- confidence
- correction
- deletion
- export

Build dedicated memory tests.

Current implementation also exposes memory through the dashboard with search, type filtering, correction, forgetting and portable export.

Success:
ReBounce can remember meaningful details after long gaps.

Current implementation: structured SQLite memories, deterministic extraction, retrieval, provenance/confidence/importance, contradiction supersession, correction, deletion and export.

Verification: GitHub Actions Stage 2-4 run #5 passed all six Windows/Linux/macOS × Python 3.13/3.14 jobs on main merge commit 4e4a1a3de782fc07793f3f7cb4a5d86933eb4ffd.

73. STAGE 3 — IDENTITY + RELATIONSHIP [VERIFIED — 2026-10-04]

Build:
- stable identity
- relationship state
- shared history
- milestones
- recurring themes
- promises
- goals
- slow personality adaptation

Success:
It feels like the same companion over time.

Current implementation: persisted interaction history, active-day tracking, recurring topics, lightweight interaction-style adaptation, milestones, goals and commitments.

Verification: Stage 1 regression run #10 and Stage 0 regression run #14 also passed all six Windows/Linux/macOS × Python 3.13/3.14 jobs on the same main merge commit.

74. STAGE 4 — POLISHED CHAT PRODUCT [VERIFIED — 2026-10-04]

Build:
- polished chat
- conversation history
- memory viewer
- relationship timeline
- activity history
- settings
- trust/permission UI

Success:
The core product is enjoyable without an avatar.

Current implementation: rendered web dashboard with Chat, Memory, Relationship, Activity, Models and Settings surfaces, plus Trust Center and data export.

Rendered UI QA: every dashboard view and visible workflow was exercised locally, including chat, memory add/correct/forget, goal/milestone/commitment actions, provider configuration/test, identity settings and export. No browser errors were observed; the final dashboard render was visually inspected.

75. STAGE 5 — VOICE

Build:
- speech-to-text
- text-to-speech
- realtime voice
- turn detection
- interruption
- voice identity
- provider abstraction
- optional local voice

Success:
Voice feels like the same companion, not text read aloud.

76. STAGE 6 — DESKTOP PRESENCE

Build:
- desktop shell
- overlay
- avatar abstraction
- animation states
- system tray
- compact companion mode
- optional pet mode

Success:
Presence feels helpful, not intrusive.

77. STAGE 7 — BOUNDED PROACTIVITY

Build:
- scheduler
- attention manager
- quiet hours
- proactive messages
- goal reminders
- unresolved-thread followups
- activity journal

Success:
ReBounce sometimes initiates useful contact without becoming noisy.

78. STAGE 8 — CURIOSITY

Build:
- user interest model
- curiosity queue
- web research
- novelty/relevance scoring
- private research notes
- suggestion flow
- budget controls

Success:
It occasionally returns with a genuinely useful discovery.

79. STAGE 9 — TOOLS + PERSONAL WORK

Build:
- MCP
- filesystem
- GitHub
- browser
- notes
- calendar
- tasks
- project workspace
- approvals
- audit logs

Success:
ReBounce can help accomplish real tasks safely.

80. STAGE 10 — VISION / SCREEN

Build:
- screenshots
- screen analysis
- window awareness
- temporary permission grants
- ephemeral visual processing
- visual context

Success:
It can understand what the user intentionally shows it without turning into surveillance software.

81. STAGE 11 — LONG-RUNNING AGENT

Build:
- planner
- durable tasks
- checkpoints
- resumable work
- recovery
- background jobs
- specialist delegation

Success:
It can pursue meaningful user-approved goals over time.

82. STAGE 12 — MULTI-DEVICE

Build:
- web
- phone
- laptop
- shared identity
- synchronized memory
- handoff
- offline queues

Success:
The companion remains the same across devices.

83. STAGE 13 — ADVANCED EMBODIMENT

Build:
- high-quality avatar
- VRM/Live2D
- expressions
- advanced animation
- shared virtual room
- persistent environment

Success:
The body enhances the relationship instead of becoming the entire product.

84. STAGE 14 — SHARED ACTIVITIES

Build:
- watch together
- listen together
- games
- study
- creative collaboration
- persistent shared world

Success:
ReBounce participates in activities, not just conversations.

85. STAGE 15 — WEARABLE / AR / PHYSICAL

Research/build:
- AI glasses
- AR
- wearables
- smart home
- haptics
- robotics

Success:
ReBounce can extend into the physical world while preserving privacy, consent and identity.

86. V1 DEFINITION

A serious V1 should probably include:
- text companion
- persistent identity
- strong memory
- relationship continuity
- memory controls
- basic goals/commitments
- polished UI
- model abstraction
- local/hybrid support
- privacy controls

Voice can be included if it does not destabilize the core architecture.

The V1 objective is not feature count.

The objective is:
“I would genuinely notice if ReBounce disappeared because it remembers our shared history.”

87. ARCHITECTURAL NON-NEGOTIABLES

- identity separate from model
- memory separate from conversation prompt
- permissions outside the model
- audit outside the model
- deterministic scheduling
- portable data format
- provider-independent interfaces
- source/provenance tracking
- recoverable actions
- inspectable state
- explicit sensor permissions

88. UI SURFACES

Long-term app can have:
- Chat
- Voice
- Companion
- Memory
- Relationship
- Activity
- Goals
- Projects
- Curiosity
- Permissions
- Models
- Settings

Do not expose every subsystem as a separate complicated screen. The primary UX should remain one companion.

89. TRUST CENTER

A future dedicated control surface should answer:
- What do you know?
- What can you see?
- What can you do?
- What did you do?
- Why did you do it?
- Where did this memory come from?
- Which model processed this?
- Did anything leave this device?

This could become a defining ReBounce feature.

90. MEMORY VISUALIZATION

Future options:
- timeline
- people graph
- project graph
- topic map
- memory clusters
- relationship history

Use visualization to help the user understand the system, not to gamify attachment.

91. COMPANION JOURNAL

A future journal could record:
- major interactions
- important decisions
- companion observations
- curiosity discoveries
- project milestones
- goals

It should remain user-readable and user-controlled.

92. PERSONAL RITUALS

Potential:
- morning check-in
- evening reflection
- weekly recap
- study ritual
- project session start
- end-of-day memory summary

These should be opt-in.

93. COMPANION HABITS

The companion can have presentation habits:
- favorite phrase
- recurring joke
- favorite media topic
- preferred way to greet
- recurring creative activity

Avoid arbitrary simulated needs designed to pressure the user.

94. PERSONALIZED SOCIAL SUPPORT

ReBounce can help the user:
- prepare for difficult conversations
- reflect before responding
- remember plans
- organize social commitments
- practice communication

It should not claim to understand another person's private mental state unless based on explicit information.

95. CONTEXT-AWARE PERSONALITY

The companion may eventually shift style based on context:
- work
- study
- gaming
- social
- creative
- rest

But this should not rewrite identity.

96. CONTEXT-AWARE MODEL ROUTING

Potential routing dimensions:
- privacy
- speed
- reasoning depth
- modality
- hardware
- token budget
- cost
- tool reliability

97. LOCAL RESOURCE AWARENESS

Long-term companion should understand available resources:
- CPU
- GPU
- VRAM
- RAM
- battery
- network
- microphone
- camera

It can avoid launching heavy models when the user is gaming or the device is low on power.

98. OFFLINE MODE

Potential offline operation:
- text
- local memory
- local voice
- local avatar
- local files
- local journal

Queued operations can run later when connectivity returns.

99. BACKUP

Future backup options:
- full backup
- memory backup
- identity backup
- conversations
- settings
- encrypted archive

Backups should be tested, not merely generated.

100. COMPANION PORTABILITY

A user should eventually be able to move:
- identity
- memories
- relationships
- projects
- settings
- journals

to another ReBounce installation.

101. PLUGIN / EXTENSION SYSTEM

Future:
- official extensions
- MCP integrations
- community adapters
- avatar packs
- voice packs
- environment packs
- tool packs

Extensions should declare:
- permissions
- data access
- actions
- version
- trust level

102. MARKETPLACE POSSIBILITY

Only later.

Could eventually host:
- avatars
- voices
- rooms
- animations
- tools
- skills
- integrations

The core companion identity and memory must not depend on the marketplace.

103. BUSINESS MODEL POSSIBILITIES

Not a current decision.

Options:
- open-source core
- self-hosted free
- hosted convenience tier
- paid cloud models
- optional premium voice/video infrastructure
- storage/sync services
- marketplace revenue
- enterprise offering

The product should avoid monetizing emotional dependency.

104. OPEN-SOURCE POSITION

Potential strategic direction:
- open companion runtime
- open memory format
- provider-independent
- local-first
- transparent permissions
- community extensions

Could be more defensible than another closed character app.

105. RESEARCH BACKLOG

Keep monitoring:
- long-term memory benchmarks
- continual learning
- preference learning
- relationship modeling
- adaptive personality
- AI attachment
- loneliness outcomes
- social substitution
- affective computing
- emotion recognition
- voice models
- speech-to-speech
- local multimodal models
- avatar animation
- computer-use agents
- tool security
- prompt injection
- memory poisoning
- agent identity
- authorization
- MCP security
- wearable AI
- AR
- robotics
- data portability
- synthetic-media regulation

106. IDEA PARKING LOT

Add ideas here instead of creating scattered documents.

Current ideas:
- relationship timeline
- memory garden
- companion journal
- curiosity
- bounded inner workspace
- companion hobbies
- shared media history
- companion traditions
- persistent virtual home
- multi-device identity
- wearable companion
- companion-to-companion coordination
- long-running personal projects
- companion dreams
- companion digital twin
- physical embodiment

107. QUESTIONS TO ANSWER BEFORE STAGE 1

Product:
- Who is the first target user?
- What is the default relationship style?
- How customizable should identity be?
- What makes ReBounce different from Nomi/Kindroid/AIRI/AILIS?

Memory:
- Build our own memory engine or integrate an existing system?
- Which memory types are mandatory in V1?
- How much memory should be injected into each prompt?
- How should contradictions work?
- How should memory be edited?

Models:
- Which local models do we support first?
- Which cloud providers are optional?
- How do we route between them?

Runtime:
- Python, TypeScript or hybrid?
- SQLite-first or another storage model?
- Event bus design?
- Background worker design?

Privacy:
- Which data stays local by default?
- What gets encrypted?
- What gets stored?
- What never gets stored?

108. DECISION PROCESS

For every major feature:
Idea
→ user value
→ competitive research
→ technical feasibility
→ cost/resource impact
→ privacy/security impact
→ architecture impact
→ prototype
→ evaluation
→ decision

109. DECISION LABELS

ADOPTED
PLANNED
EXPERIMENT
RESEARCH
BACKLOG
DEFERRED
BLOCKED
REJECTED

110. CURRENT DECISIONS

| Decision | Status | Reason |
| --- | --- | --- |
| One persistent companion identity | ADOPTED | Core product; user chooses companion name |
| Model/provider independence | ADOPTED | Prevent lock-in |
| Memory as first-class subsystem | ADOPTED | Continuity |
| User memory controls | ADOPTED | Trust |
| Bounded autonomy | ADOPTED | Useful agency |
| Deterministic permissions | ADOPTED | Safety |
| Audit log | PLANNED | Trust |
| Local/hybrid capability | PLANNED | Privacy/resilience |
| Voice | PLANNED | Presence |
| Desktop presence | PLANNED | Embodiment |
| Proactivity | PLANNED | Initiative |
| Curiosity | EXPERIMENT | Differentiation |
| MCP | PLANNED | Tool ecosystem |
| Vision | PLANNED | Multimodality |
| Multi-device | RESEARCH/PLANNED | Continuity |
| AR/VR | RESEARCH | Future surface |
| Robotics | RESEARCH | Speculative |

111. IMPORTANT NON-GOALS

Do not start with:
- full 3D world
- robotics
- AR
- custom foundation model
- social network
- huge character marketplace
- unrestricted computer control
- dozens of integrations
- complex monetization
- multi-agent swarm
- child-targeted companion

111A. CI VERIFICATION / FAILURE-RECOVERY RULE

GitHub Actions is part of the definition of done.

For every code change that triggers CI:
1. Check the resulting GitHub Actions run.
2. Inspect every required job and its conclusion.
3. If any required job fails, inspect the failure logs.
4. Diagnose the actual root cause.
5. Fix the code/workflow/test.
6. Commit the fix.
7. Check the new GitHub Actions run again.
8. Repeat until all required checks are green.
9. Do not mark the stage complete while required CI checks are red or unverified.

An old failed run does not count as current verification; verification must correspond to the current/fixed commit.

112. STAGE COMPLETION RULE

A stage is not “done” because code compiles.

For each stage:
implementation
→ automated tests
→ real rendered UI
→ interactive inspection
→ failure testing
→ state/memory verification
→ security/privacy check
→ performance check
→ fixes
→ rerun

For UI-heavy work, every visible button, tab, toggle, control and interaction must be inspected in the actual rendered interface.

113. THE NORTH STAR

The ambitious long-term interpretation of ReBounce is:

A persistent personal digital companion that maintains a durable identity, understands the user's evolving life, learns from shared experiences, communicates through multiple modalities, has bounded initiative, can perform useful work with permission, and can inhabit many digital and physical interfaces without losing continuity.

114. WHAT SUCCESS FEELS LIKE

Not:
- “The avatar looks cool.”
- “The model benchmark is high.”
- “We have 100 tools.”

Success is:

The user can speak to ReBounce today, next week and months later and still feel that it is the same companion.

It remembers what matters.
It knows when context changed.
It occasionally finds something genuinely useful.
It knows when to stay quiet.
It can help accomplish real things.
It does not hide its actions.
It does not try to control the user's life.
The user can inspect, correct, export and delete its memory.
The user can replace the underlying model without losing the relationship.

115. SOURCE MAP — COMPANIONS

Replika memory:
https://help.replika.com/hc/en-us/articles/37208679176077-How-does-Replika-s-memory-work

Replika what it remembers:
https://help.replika.com/hc/en-us/articles/360000874712-What-does-Replika-remember-about-me

Replika how it works:
https://help.replika.com/hc/en-us/articles/4410750221965-How-does-Replika-work

Nomi knowledge base:
https://wiki.nomi.ai/

Nomi memory and knowledge:
https://wiki.nomi.ai/How_does_Nomi_memory_and_knowledge_work%3F

Nomi proactive messages:
https://wiki.nomi.ai/What_Are_Proactive_Messages%3F

Nomi voice calls:
https://wiki.nomi.ai/index.php?title=Can_I_call_my_Nomi_and_how_do_hands-free_calls_work%3F

Kindroid memory:
https://kindroid.ai/v2/docs/memory/

Kindroid chat/features/proactivity:
https://kindroid.ai/v2/docs/chat-features-and-tools/

Kindroid group chats:
https://kindroid.ai/v2/docs/groupchats/

Kindroid voice/video:
https://kindroid.ai/v2/docs/voice-calls-and-video-calls/

Character.AI memory:
https://blog.character.ai/memory/

116. SOURCE MAP — RESEARCH

LongMemEval:
https://arxiv.org/abs/2410.10813

LoCoMo:
https://aclanthology.org/2024.acl-long.747/

AI attachment scale:
https://www.sciencedirect.com/science/article/pii/S2451958825003276

AI companionship and attachment:
https://www.sciencedirect.com/science/article/pii/S0268401225000222

AI companions and subjective well-being:
https://www.sciencedirect.com/science/article/pii/S0160791X26000187

AI companions and psychological well-being:
https://www.nature.com/articles/s41562-026-02516-2

Human peer vs supportive chatbot loneliness:
https://www.sciencedirect.com/science/article/pii/S0022103126000417

Digital companionship among young adults in India:
https://www.sciencedirect.com/science/article/pii/S0001691826002684

Anthropomorphic AI / digital entrapment:
https://www.sciencedirect.com/science/article/pii/S2444569X25001805

Affective computing survey:
https://arxiv.org/abs/2505.01542

117. SOURCE MAP — MEMORY / AGENTS

Mem0 architecture:
https://github.com/mem0ai/mem0/blob/main/skills/mem0/references/architecture.md

Hindsight:
https://github.com/vectorize-io/hindsight

Hindsight consistency guide:
https://github.com/vectorize-io/hindsight/blob/main/hindsight-docs/guides/2026-04-23-guide-how-memory-helps-ai-agents-stay-consistent.md

Hindsight memory defense and curation:
https://github.com/vectorize-io/hindsight/blob/main/hindsight-docs/blog/2026-06-12-version-0-8-2.md

Hindsight consolidation:
https://github.com/vectorize-io/hindsight/blob/main/hindsight-docs/blog/2026-05-21-agent-memory-consolidation.md

2026 memory benchmark overview:
https://mem0.ai/library/agent-memory/ai-memory-benchmarks-in-2026

118. SOURCE MAP — OPEN SOURCE COMPANIONS

AILIS:
https://github.com/haowenGuo/AILIS

Miru:
https://github.com/kiyotakali/Miru

Smart Pet Agent:
https://github.com/realstreetsmartnyc/smart-pet-agent

Open-LLM-VTuber/AIRI lineage:
https://github.com/RobertHan96/airi

Desktop pet example:
https://github.com/valerieliang/desktop-pet

Screen-aware desktop pet example:
https://github.com/NatBrian/mochi-llm-pet

VRM companion:
https://github.com/ARPAHLS/avatar

UniPet:
https://github.com/ydyangdan/UniPet/blob/main/docs/VISION.md

YuriOS:
https://github.com/yuri-os/YuriOS

119. SOURCE MAP — REALTIME

OpenAI Realtime API:
https://developers.openai.com/api/docs/guides/realtime

OpenAI voice agents:
https://developers.openai.com/api/docs/guides/voice-agents

LiveKit:
https://docs.livekit.io/agents/

LiveKit multimodality:
https://docs.livekit.io/agents/multimodality/

Gemini Live API:
https://ai.google.dev/gemini-api/docs/live-api/get-started-sdk

Moshi:
https://github.com/kyutai-labs/moshi

120. SOURCE MAP — TOOLS / SECURITY

MCP:
https://modelcontextprotocol.io/

MCP 2026-07-28:
https://blog.modelcontextprotocol.io/posts/2026-07-28/

OpenAI sandbox agents:
https://developers.openai.com/api/docs/guides/agents/sandboxes

OWASP Top 10 for Agentic Applications 2026:
https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/

OWASP Agentic Threats Navigator:
https://genai.owasp.org/resource/owasp-gen-ai-security-project-agentic-threats-navigator/

OWASP Securing Agentic Applications:
https://genai.owasp.org/resource/securing-agentic-applications-guide-1-0/

OWASP Agent Control Standard:
https://genai.owasp.org/resource/agent-control-standard-acs/

OWASP State of Agentic Security and Governance:
https://genai.owasp.org/resource/state-of-agentic-ai-security-and-governance/

121. SOURCE MAP — PRIVACY / REGULATION

India MeitY:
https://www.meity.gov.in/documents/act-and-policies

India DPDP explanatory note:
https://www.meity.gov.in/writereaddata/files/Explanatory-Note-DPDP-Rules-2025.pdf

EU AI Act:
https://eur-lex.europa.eu/eli/reg/2024/1689/2026-07-27/eng

EU transparency:
https://digital-strategy.ec.europa.eu/en/factpages/quick-facts-transparency-rules-ai-systems

UK 2026 chatbot/children response:
https://www.gov.uk/government/consultations/growing-up-in-the-online-world-a-national-consultation/outcome/growing-up-in-the-online-world-government-response-july-2026

FTC companion chatbot inquiry:
https://search.ftc.gov/news-events/news/press-releases/2025/09/ftc-launches-inquiry-ai-chatbots-acting-companions

122. SOURCE MAP — WEARABLES

Meta wearable developer platform:
https://developers.meta.com/wearables/

Meta Wearables Device Access Toolkit:
https://developers.meta.com/wearables/device-access-toolkit/

Meta AI glasses recap:
https://developers.meta.com/blog/meta-connect-recap-ai-glasses/

123. RESEARCH CAVEATS

- Vendor documentation describes features but does not equal independent validation.
- Reddit reports are useful for pain-point discovery, not causal scientific evidence.
- Many psychology studies are observational, cross-sectional or short-term.
- AI products evolve rapidly.
- Legal requirements differ by jurisdiction.
- Some theoretical features may never become technically, commercially or ethically appropriate.
- ReBounce decisions should be revised when better evidence appears.

124. 2026-10-04 INITIAL DECISION

Initial strategic conclusion:

Build ReBounce as a persistent companion runtime, not as a character chatbot.

Start with:
identity
memory
relationship continuity
trust/control
conversation

Then progressively add:
voice
presence
proactivity
curiosity
tools
vision
long-running work
multi-device
embodiment
AR/VR/wearables
physical systems

This document is intentionally the place where the project grows.

When we get a new idea during development, add it here first.
When research changes our assumptions, update the relevant section.
When we make a real architectural decision, record it here.
When a feature becomes a build target, assign it to a stage.

125. NEXT ACTION

Stage 0 begins by turning this research into the actual engineering foundation:

1. choose the runtime stack
2. design the minimum data model
3. design the model-provider interface
4. design the memory interface
5. design the event model
6. design deterministic permissions
7. create the first companion brain prototype
8. define the first longitudinal evaluation suite

Only after that should we commit to major UI/embodiment work.

END STATE TO REMEMBER

Capability may grow almost indefinitely.
The identity may evolve.
The memory may deepen.
The body may change.
The model may change.
The devices may change.

The underlying principle should not:

ReBounce becomes more capable over time without becoming less understandable, less portable, or less controllable.


126. STAGE 0 ENGINEERING BASELINE — 2026-10-04

Status:
IMPLEMENTED — verification pending on a real development machine.

Repository baseline:
- Python 3.13+ core
- Standard-library-first Stage 0
- SQLite durable store
- model-provider protocol
- deterministic permission policy
- event model
- companion identity contract
- minimal companion runtime
- automated unittest coverage
- OS-agnostic domain layer

Stack decision:
- Language: Python 3.13+
- Core runtime dependencies: standard library only for Stage 0
- Storage: SQLite
- Async style: Python asyncio where runtime contracts require it
- Web/API framework: deferred until Stage 1 needs a concrete API surface
- Frontend: deferred until core behavior is validated
- Model SDK/provider dependency: deferred behind ModelProvider
- Desktop framework: deferred until desktop presence stage

Reason for the dependency-light foundation:
The companion core should remain portable and easy to run on Windows, Linux and macOS. Python's sqlite3 module provides a built-in SQL interface and SQLite is specifically suitable for internal application storage and later migration to a larger database if required. SQLAlchemy's current asyncio/SQLite support was reviewed, but introducing an ORM is intentionally deferred until the storage/query complexity justifies it.

Engineering contracts now present in the repository:
- CompanionIdentity
- ModelProvider / ModelMessage / ModelResponse
- Event / EventType
- PermissionPolicy / ActionLevel
- SQLiteStore
- CompanionRuntime
- Stage 0 unittest suite

Stage 0 storage domains currently represented:
companions
conversations
messages
memories
events
permissions

Verification required before declaring Stage 0 fully complete:
- install package on Windows
- install package on Linux
- install package on macOS
- run Stage 0 tests
- verify a fresh database is created correctly
- verify conversation/message/event persistence
- verify deterministic permission behavior
- verify Python 3.14 compatibility

Current implementation intentionally does NOT include:
- real model provider
- memory retrieval/consolidation
- authentication
- UI
- voice
- web browsing
- tool execution
- autonomous background jobs

Those belong to later stages.

127. STAGES 10–15 IMPLEMENTATION — 2026-10-04

Status:
IMPLEMENTED — automated verification pending.

Stage 10 — Vision / Screen
- expiring screen-sharing sessions
- explicit screen permission
- ephemeral visual context
- screenshot content represented by a SHA-256 hash rather than persisted raw capture
- window/application/URL context fields

Stage 11 — Long-running Agent
- durable plans and jobs
- approval-required plans by default
- durable checkpoints
- stale-worker recovery
- bounded specialist delegation

Stage 12 — Multi-device
- device registry and heartbeats
- ordered synchronization event cursor
- offline operation queue
- expiring handoff tokens containing minimal continuity cursors

Stage 13 — Advanced Embodiment
- embodiment profiles
- CSS-orb / Live2D / VRM asset references
- expression and animation configuration
- persistent companion room and room objects

Stage 14 — Shared Activities
- watch, listen, game, study and creative activity sessions
- pause/complete state
- activity event timeline
- persistent activity state

Stage 15 — Wearable / AR / Physical
- adapter-first physical device registry
- disabled-by-default real-device controls
- explicit permission layers for smart-home, wearable and robotics resources
- approval-required physical commands
- simulator transport for safe testing

