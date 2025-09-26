const createDaisyUIThemes = (
  darkTheme: string,
  lightTheme: string,
  themes: string[],
) => {
  return themes
    .map((theme) => {
      if (theme === lightTheme) return `${theme} --default`;
      if (theme === darkTheme) return `${theme} --prefersdark`;
      return theme;
    })
    .join(", ");
};
// export const themes = ["coffee", "night", "retro", "nord", "dracula"];
export const themes = [
  "coffee",
  "night",
  "retro",
  "dracula",
  "undercity",
  "daydream",
];
export const lightTheme = "daydream";
// export const darkTheme = "coffee";
export const darkTheme = "daydream";
export const daisyUIThemes = createDaisyUIThemes(darkTheme, lightTheme, themes);

export const loadingTextOptions = [
  "Testing limits... and then breaking them.",
  "Pushing the boundaries of logic.",
  "Shaking the system until it behaves.",
  "Tweaking the universe's variables.",
  "Speed-running through the codebase.",
  "Breaking the laws of time... or just the code.",
  "Trying to make this load faster than light.",
  "Calculating all possibilities... and then some.",
  "Telling the CPU to hold my coffee.",
  "Finding the edge case no one saw coming.",
  "Messing with the fabric of time complexity.",
  "Creating opportunities for unexpected crashes.",
  "Thinking outside the brackets.",
  "Overclocking ideas for maximum speed.",
  "Asking for trouble... and finding it.",
  "Poking the system to see what breaks.",
  "Pushing through the bounds of reason.",
  "Striving to break the unbreakable.",
  "Walking the fine line between genius and chaos.",
  "Waiting for the perfect moment to strike.",
  "Making sense of the nonsensical.",
  "Giving the CPU a pep talk.",
  "Testing the limits of what's possible.",
  "Feeding the servers some good vibes.",
];

export const eventSlugAliases = {
  rec8sacRO9Yj6edPG: "scrapyard-flagship",
};

// node --loader ts-node/esm src/lib/consts.ts
// console.log("Generated DaisyUI Themes:");
// console.log(createDaisyUIThemes(darkTheme, lightTheme, themes));
