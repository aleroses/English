const filterWords = () => {
  let arrayList = $$("a.dictLink.featured, a.dictLink");

  let rawWords = [];
  let previousList = [];
  let finalList = [];

  const exclude =
    /algo\/a|algo|a algn\.|\(.*\)|lgn\.|algo\/a algn\.|a algo\/a algn./g;

  rawWords = arrayList.map((word) => word.textContent);

  previousList = rawWords.map((word) => {
    return word.replace(exclude, "").replace(/\s+/g, " ").trim();
  });

  const firstWord = rawWords[0].split(" ")[0];

  finalList = previousList.filter((item) => {
    return !item.includes(firstWord);
  });

  console.clear();
  console.log(finalList.length);
  console.log(finalList.join("\n"));

  copy(finalList.join("\n"));
};
