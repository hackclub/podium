<script lang="ts">
  let { satellite, height = 64 }: { satellite: string; height?: number } = $props();
</script>

<svg
  height={height+16}
  viewBox="-2 0 130 62"
  fill="none"
  overflow="visible"
  xmlns="http://www.w3.org/2000/svg"
>
  <g filter="url(#filter0_d_32_978)">
    <text
      transform="translate(0 5.76892) rotate(-2.75552)"
      fill="#FCF5ED"
      style="white-space: pre"
      xml:space="preserve"
      font-family="DREAM PLANNER"
      font-size="37.5"
      letter-spacing="0em"><tspan x="0" y="28.5187">CAMPFIRE</tspan></text
    >
  </g>
  <g filter="url(#filter1_d_32_978)">
    <text
      transform="translate(60.6625 38.8909) rotate(-2.75552)"
      fill="#FCF5ED"
      style="white-space: pre"
      xml:space="preserve"
      font-family="DREAM PLANNER"
      font-size="16"
      letter-spacing="0em"
      ><tspan x="0.609375" y="11.988">{satellite.toUpperCase()}</tspan></text
    >
  </g>
  <defs>
    <filter
      id="filter0_d_32_978"
      x="1.04883"
      y="2.38037"
      width="120.781"
      height="35.7594"
      filterUnits="userSpaceOnUse"
      color-interpolation-filters="sRGB"
    >
      <feFlood flood-opacity="0" result="BackgroundImageFix" />
      <feColorMatrix
        in="SourceAlpha"
        type="matrix"
        values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
        result="hardAlpha"
      />
      <feOffset dx="1.5" dy="3" />
      <feComposite in2="hardAlpha" operator="out" />
      <feColorMatrix
        type="matrix"
        values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"
      />
      <feBlend
        mode="normal"
        in2="BackgroundImageFix"
        result="effect1_dropShadow_32_978"
      />
      <feBlend
        mode="normal"
        in="SourceGraphic"
        in2="effect1_dropShadow_32_978"
        result="shape"
      />
    </filter>
    <filter
      id="filter1_d_32_978"
      x="59"
      y="34"
      width="68"
      height="24"
      filterUnits="userSpaceOnUse"
      color-interpolation-filters="sRGB"
    >
      <feFlood flood-opacity="0" result="BackgroundImageFix" />
      <feColorMatrix
        in="SourceAlpha"
        type="matrix"
        values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0"
        result="hardAlpha"
      />
      <feOffset dx="1.5" dy="3" />
      <feComposite in2="hardAlpha" operator="out" />
      <feColorMatrix
        type="matrix"
        values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"
      />
      <feBlend
        mode="normal"
        in2="BackgroundImageFix"
        result="effect1_dropShadow_32_978"
      />
      <feBlend
        mode="normal"
        in="SourceGraphic"
        in2="effect1_dropShadow_32_978"
        result="shape"
      />
    </filter>
  </defs>
</svg>
