<script lang="ts">
  import { sessions } from "../../lib/store";
  import SessionView from "../SessionView.svelte";

  let session = $derived($sessions.at(-1));
</script>

{#if !session}
  <p class="muted" style="padding: 24px">No session data yet — scan replays to get started.</p>
{:else}
  <SessionView {session} />
{/if}
