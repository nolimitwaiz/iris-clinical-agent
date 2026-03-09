# React Voice First Frontend

Date: 2026-03-01
Status: Decided

## Context

The Streamlit frontend was a dense 3 column text dashboard. For ARPA-H demo and real patient use, we need a voice first interface where patients tap to speak and hear Iris respond. Clinicians need a separate view with full Action Packet transparency. The patient should never see clinical internals.

## Decision

Build a React app (Vite + TypeScript) in `frontend/` with two routes:

- `/` PatientView: Full screen black canvas with animated radial node orb
- `/clinician` ClinicianView: 3 column dashboard matching existing Streamlit layout

### Patient View Design

```
+------------------------------------------+
|  [Patient Selector]     [Clinician View] |
|                                          |
|                                          |
|              ○ ○ ○ ○ ○                   |
|            ○    ORB    ○                 |
|              ○ ○ ○ ○ ○                   |
|                                          |
|         "Tap the orb to speak"           |
|                                          |
|         [Or type instead]                |
+------------------------------------------+
```

### Radial Node Orb (RadialNodes.tsx)

80 animated nodes on a canvas using Fibonacci sphere distribution for even spacing.

| State | Color | Behavior |
|-------|-------|----------|
| idle | Soft blue (#508CFF) | Slow drift, gentle pulse |
| listening | Green (#32DC82) | Inward breathing rhythm, faster pulse |
| thinking | Amber (#FFBE32) | Fast orbital rotation |
| speaking | Cyan (#00DCFF) | Outward wave pulses |

Nodes have:
- Spherical coordinates projected to 2D
- Per node speed variation for organic feel
- Depth based opacity and size (z sorting illusion)
- Subtle connection lines between nearby nodes
- Central glow gradient per state

### Voice Flow

```
1. User taps orb → state = listening, MediaRecorder starts
2. User taps again → state = thinking, recording stops, POST audio to /api/chat
3. Server responds → state = speaking, play TTS audio (or browser speechSynthesis fallback)
4. Audio ends → state = idle
```

### Clinician View Design

```
+----------+------------------+-------------+
| Patient  |  Conversation    | Clinical    |
| Dashboard|  Monitor         | Reasoning   |
|          |                  |             |
| Name/Age | [Patient msg]    | [Packet 1]  |
| EF/NYHA  |                  | [Packet 2]  |
| Meds     | [Iris response]  | [Packet 3]  |
| Labs     |                  | ...         |
| Social   | [Input box]      | [Escalation]|
+----------+------------------+-------------+
```

### Component Structure

```
frontend/src/
  App.tsx                      Router: / and /clinician
  api/
    client.ts                  fetch wrapper for FastAPI
    types.ts                   TypeScript types matching Pydantic schemas
  views/
    PatientView.tsx            Full screen voice orb
    ClinicianView.tsx          3 column dashboard
  components/
    orb/
      RadialNodes.tsx          80 node canvas animation
      useOrbState.ts           State machine: idle > listening > thinking > speaking
    clinician/
      ActionPacketCard.tsx     Color coded packet display
      PatientDashboard.tsx     Meds, labs, vitals, social factors
      EscalationAlert.tsx      Red/yellow alert for escalations
  hooks/
    useAudioRecorder.ts        MediaRecorder API, produces base64
```

### Color Coding (ActionPacketCard)

Matches `transparency_panel.py` exactly:

| Color | Decisions |
|-------|-----------|
| Green | safe, feasible, adherent, no_escalation, low, maintain, no_change |
| Yellow | moderate, barrier_identified, non_adherent, hold |
| Red | blocked, escalate, critical, high, stop |
| Blue | increase, start |

## Alternatives Considered

1. **Enhance Streamlit with audio:** Rejected. Streamlit has no native audio recording, canvas animations, or client side state management needed for voice interaction.
2. **Next.js instead of Vite:** Rejected. No server side rendering needed. Vite is simpler and faster for a single page app.
3. **Single view with toggle:** Rejected. Patient and clinician views have fundamentally different information needs. Separate routes enforce separation.
4. **WebGL/Three.js for orb:** Rejected. 2D canvas with 80 nodes is sufficient for the effect. WebGL adds dependency weight without visual benefit at this scale.

## Consequences

- Patient sees only the orb and hears voice responses. No clinical data exposed.
- Clinician sees full pipeline transparency, can monitor conversations and debug.
- Voice interaction requires microphone permission (browser prompt on first use).
- Text input available as fallback (toggle at bottom of patient view).
- Browser `speechSynthesis` provides TTS fallback if Gemini TTS fails.
- React app builds to static files (deployable to any static host).
