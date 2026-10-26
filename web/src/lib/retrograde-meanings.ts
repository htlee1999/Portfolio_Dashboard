/**
 * What each planet's retrograde means in Western astrology, paraphrased from the sources below.
 * This is astrological tradition, not astronomy: the dates on the page are measured, these readings aren't.
 */

export const MEANING_SOURCES = {
  cafeMercury: { label: "Cafe Astrology: Mercury Retrograde", url: "https://cafeastrology.com/mercuryretrograde.html" },
  cafeVenus: { label: "Cafe Astrology: Venus Retrograde", url: "https://cafeastrology.com/venusretrograde.html" },
  cafeSaturn: { label: "Cafe Astrology: When Saturn is Retrograde", url: "https://cafeastrology.com/when-saturn-is-retrograde.html" },
  cafeRetrogrades: { label: "Cafe Astrology: Retrograde Cycles and Stations", url: "https://cafeastrology.com/retrogrades.html" },
  almanacGuide: { label: "The Old Farmer's Almanac: Planetary Retrogrades Guide", url: "https://www.almanac.com/planetary-retrogrades-guide-mercury-venus-mars-more" },
  almanacMars: { label: "The Old Farmer's Almanac: Mars Retrograde", url: "https://www.almanac.com/mars-retrograde-when-mars-retrograde" },
  astrologyJupiter: { label: "Astrology.com: Jupiter Retrograde", url: "https://www.astrology.com/retrograde/jupiter-retrograde" },
  astrostyle: { label: "Astrostyle: What Is Retrograde", url: "https://astrostyle.com/astrology/retrogrades/" },
  abcMercury: { label: "ABC7: Mercury Retrograde, what it is and how it affects you", url: "https://abc7news.com/post/mercury-retrograde-what-it-is-and-how-it-affects-you/5387488/" },
} as const;

export type MeaningSource = keyof typeof MEANING_SOURCES;

export type RetroMeaning = {
  /** What the planet governs. */
  rules: string;
  /** How often and how long, as astrologers describe it. */
  cycle: string;
  /** One line for the day detail. */
  theme: string;
  reading: string;
  goodFor: string[];
  avoid: string[];
  sources: MeaningSource[];
};

export const MEANINGS: Record<string, RetroMeaning> = {
  mercury: {
    rules: "Communication, thinking, contracts and paperwork, buying and selling, travel, mail and technology",
    cycle: "3–4 times a year, about 3 weeks each (around 18% of the time)",
    theme: "communication, contracts, travel and tech",
    reading:
      "The best-known retrograde. Because Mercury governs how we take in and pass on information, its retrogrades are associated with misunderstandings, delays, travel disruption, technology glitches and second thoughts. Decisions made now are said to be likely to change once Mercury turns direct. The station days at either end are said to be the most disruptive.",
    goodFor: ["Reviewing, editing and redoing work", "Revisiting old plans or subjects you studied before", "Reconnecting with old contacts", "Looking for lost items", "Reflection and journaling"],
    avoid: ["Signing contracts", "Major decisions", "Launching a business or new venture", "Being careless with personal data or paperwork"],
    sources: ["cafeMercury", "abcMercury"],
  },
  venus: {
    rules: "Love and relationships, what we value, money, beauty, art, pleasure and social life",
    cycle: "About every 18 months, for 40–43 days",
    theme: "love, money and values",
    reading:
      "A time for reassessing what, and who, we value. Past partners or old relationship issues are said to resurface; weak relationships may end while strong ones hold. Judgement about love, money and appearance is considered unreliable, so people often change their minds afterwards.",
    goodFor: ["Making budgets and financial plans", "Rethinking relationships and what you need from them", "Finding unusual bargains, if you're careful"],
    avoid: ["Weddings and starting new relationships", "Big purchases or financial commitments", "Makeovers, cosmetic procedures, renovating and redecorating"],
    sources: ["cafeVenus"],
  },
  mars: {
    rules: "Drive, action, energy, ambition, courage, anger and competition",
    cycle: "About every 2 years, lasting roughly 2–2½ months",
    theme: "drive, action and conflict",
    reading:
      "Mars retrograde is said to feel as though the fire has gone out: motivation and courage dip, progress takes extra effort, and frustration builds. Old conflicts and shelved projects are said to resurface. The usual advice is to pause before reacting and to rethink where you put your energy.",
    goodFor: ["Rethinking goals and where your energy goes", "Returning to stalled projects", "Slowing down and pausing before acting"],
    avoid: ["Starting a business", "Starting a lawsuit", "Picking fights; whoever starts one is said to lose", "Risky ventures"],
    sources: ["almanacMars", "almanacGuide"],
  },
  jupiter: {
    rules: "Growth, luck, abundance, beliefs, higher learning and long-distance travel",
    cycle: "Once a year, about 4 months",
    theme: "growth, beliefs and luck",
    reading:
      "Jupiter's expansive energy is said to turn inward. Instead of outward growth, it's a time to reassess beliefs, ethics and what 'enough' means, with detours and course corrections in the area of life it's moving through.",
    goodFor: ["Inner, spiritual or philosophical growth", "Reaffirming your values", "Course-correcting long-term plans"],
    avoid: ["Over-expanding or over-committing"],
    sources: ["astrologyJupiter", "almanacGuide"],
  },
  saturn: {
    rules: "Structure, responsibility, discipline, limits, time and long-term foundations",
    cycle: "Once a year, about 4½ months (around 38% of the time)",
    theme: "duties, structure and limits",
    reading:
      "Around the station, responsibilities can feel heavy and motivation may dip. The retrograde itself is read as a time to review rules, structures and commitments, simplify, and fix earlier mistakes. Delays are said to give a chance to refine the work.",
    goodFor: ["Reviewing commitments and simplifying", "Correcting errors and refining work", "Finishing or returning to old projects"],
    avoid: ["Taking on major new projects or extra responsibilities"],
    sources: ["cafeSaturn"],
  },
  uranus: {
    rules: "Change, innovation, freedom, rebellion and technology",
    cycle: "Once a year, about 5 months",
    theme: "change, freedom and technology",
    reading:
      "Uranus's push for sudden change is said to slow down. It's read as a check-in before a breakthrough, with a restless urge for freedom. As the ruler of electronics, its retrogrades are said to bring Mercury-like tech trouble.",
    goodFor: ["Updating digital security and privacy settings", "Reflecting before making big changes"],
    avoid: ["Impulsive rebellion for its own sake"],
    sources: ["astrostyle", "almanacGuide"],
  },
  neptune: {
    rules: "Dreams, intuition, spirituality, imagination and illusion",
    cycle: "Once a year, about 5 months",
    theme: "dreams, illusions and intuition",
    reading:
      "Read as a reality check: the rose-coloured glasses come off and illusions fade, which can be uncomfortable but clarifying. It's said to be a deeply introspective time.",
    goodFor: ["Confronting self-deception", "Spiritual and creative reflection"],
    avoid: ["Ignoring uncomfortable truths"],
    sources: ["astrostyle", "almanacGuide"],
  },
  pluto: {
    rules: "Power, transformation, endings and rebirth, and the subconscious",
    cycle: "Once a year, about 5 months",
    theme: "power and transformation",
    reading:
      "Pluto's intensity is said to ease, opening space for inner work: looking at your relationship with power and digging out and releasing old patterns.",
    goodFor: ["Deep inner work and therapy-style reflection", "Letting go of old issues"],
    avoid: ["Power struggles"],
    sources: ["astrostyle", "almanacGuide"],
  },
};

/** Ideas that apply to every retrograde. */
export const GENERAL_NOTES: { title: string; text: string; sources: MeaningSource[] }[] = [
  {
    title: "Retrograde",
    text: "The planet doesn't actually reverse; Earth overtakes it (or it overtakes Earth), so it seems to slide backwards. In astrology this marks a time to review, reassess and redo in the areas the planet governs, rather than to start new things.",
    sources: ["almanacGuide", "cafeMercury"],
  },
  {
    title: "Stations",
    text: "The days a planet appears to stop and turn, either retrograde or direct. Its influence is said to be strongest then, and they're considered the most unsettled days of the cycle.",
    sources: ["cafeRetrogrades", "cafeMercury"],
  },
  {
    title: "Shadow",
    text: "The stretch of the zodiac the retrograde covers twice. The pre-shadow opens when the planet first reaches the degree where it will later turn direct. The post-shadow closes when it returns to the degree where it turned retrograde. Its themes are said to build up and wind down across this period; for new long-term ventures, the post-shadow is considered better than the pre-shadow.",
    sources: ["cafeRetrogrades", "cafeMercury"],
  },
  {
    title: "Inner vs outer planets",
    text: "Mercury, Venus and Mars retrogrades are said to be felt personally and directly. Jupiter through Pluto are retrograde for months every year, and their effect is described as subtler and more collective. At least one planet is retrograde most of the time.",
    sources: ["almanacGuide", "astrostyle"],
  },
];
