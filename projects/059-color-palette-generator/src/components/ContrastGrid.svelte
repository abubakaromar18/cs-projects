<script>
  // Pairwise WCAG contrast matrix: which palette colors can be used as
  // text-on-background together? Cells that fail can be "fixed" by nudging
  // the text color's lightness until it passes AA.
  import { contrastRatio, ensureContrast, wcagRating } from '../lib/color.js';

  let { hexes, onfix } = $props();

  const rows = $derived(
    hexes.map((bg) =>
      hexes.map((fg) => {
        const ratio = contrastRatio(fg, bg);
        return { fg, bg, ratio, rating: wcagRating(ratio) };
      }),
    ),
  );
</script>

<div class="wrap">
  <table>
    <caption>Contrast matrix — text color (column) on background (row)</caption>
    <thead>
      <tr>
        <th scope="col"></th>
        {#each hexes as hex, j (j)}
          <th scope="col"><span class="dot" style:background={hex}></span>{hex}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each rows as row, i (i)}
        <tr>
          <th scope="row"><span class="dot" style:background={hexes[i]}></span>{hexes[i]}</th>
          {#each row as cell, j (j)}
            <td style:background={cell.bg} style:color={cell.fg}>
              {#if i === j}
                <span class="na">—</span>
              {:else}
                <span class="aa">Aa</span>
                <small>{cell.ratio.toFixed(1)} · {cell.rating}</small>
                {#if cell.ratio < 4.5}
                  {@const fixed = ensureContrast(cell.fg, cell.bg, 4.5)}
                  {#if fixed}
                    <button
                      class="fix"
                      title={`Change ${cell.fg} to ${fixed} to reach AA`}
                      onclick={() => onfix(j, fixed)}
                    >fix → {fixed}</button>
                  {/if}
                {/if}
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .wrap { overflow-x: auto; }
  table { border-collapse: separate; border-spacing: 4px; font-size: 0.8rem; }
  caption { text-align: left; color: var(--muted); padding-bottom: 0.4rem; }
  th { font-family: ui-monospace, monospace; font-weight: 500; white-space: nowrap; padding: 0 0.3rem; }
  .dot { display: inline-block; width: 0.8em; height: 0.8em; border-radius: 50%; margin-right: 0.3em; vertical-align: middle; border: 1px solid var(--border); }
  td { min-width: 6.5rem; height: 4.2rem; border-radius: 6px; text-align: center; vertical-align: middle; }
  .aa { display: block; font-weight: 700; font-size: 1.1rem; }
  small { display: block; }
  .na { opacity: 0.4; }
  .fix {
    margin-top: 0.2rem;
    padding: 0.05rem 0.35rem;
    font-size: 0.68rem;
    background: rgba(255, 255, 255, 0.85);
    color: #000;
    border-color: transparent;
    font-family: ui-monospace, monospace;
  }
</style>
