# Component 13 - Twilio Media Streams + Audio Codec - Plan

1. Add `@fastify/websocket` to deps.
2. Audio codec: `src/audio_codec/{ulaw,resample,index}.ts`.
3. Twilio WS types in `src/twilio_ws/types.ts`.
4. Handler at `src/twilio_ws/handler.ts`. Manages `activeStreams` Map.
5. Register the handler in `server.ts`.
6. Unit tests for the codec and resample.

