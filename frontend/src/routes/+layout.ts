// Until fetch is passed to the API client, this should prevent from the client being authenticated but an unauthenticated request being made from the server
export const ssr = false;

// Provide default meta tags for all pages
export const load = () => {
  return {
    meta: [
      {
        name: "description",
        content: "Podium - Hack Club's open-source peer-judging platform for hackathons"
      }
    ]
  };
};
