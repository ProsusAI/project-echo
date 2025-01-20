const state = () => ({
  examples: [
    {
        "id": 1,
        "title": "Podcasts - All Levels at Prosus",
        "icon": "heroicons-outline:light-bulb",
        "messages": [
            "Produce a podcast episode where CEO John Carter shares insights on cultivating a growth mindset in leadership with HR expert Anna Williams. Incorporate practical advice from project manager Clara Gomez, who discusses how her team embraced this mindset to overcome challenges, and behavioral psychologist Dr. Michael Lee exploring the psychological benefits of fostering a growth-oriented culture.",
            "Host a podcast discussing diversity and inclusion, featuring D&I officer Emily Clark who talks about Prosus' initiatives with inclusion strategist Rahul Gupta. Include a case study from a team leader who successfully implemented D&I practices, and an employee named John Kim sharing his experience in a diverse team.",
            "Create an episode focused on work-life balance where wellness coach Lisa Matthews discusses strategies for maintaining balance with operations director Tom Reynolds. Add personal stories from employees who found effective ways to balance work and life, and psychologist Dr. Sarah Roberts offering mental well-being tips.",
            "Research the latest trends in remote work and develop a podcast episode that discusses how Prosus employees are adapting to hybrid working environments. Include interviews with remote work experts and practical tips for staying productive."
        ]
    },
    {
        "id": 2,
        "title": "Podcasts - C-Level Executives at Prosus",
        "icon": "heroicons-outline:light-bulb",
        "messages": [
            "Develop a podcast where COO Maria Lopez delves into global expansion strategies with business analyst Dr. Robert Chang. Include insights from CFO David Greene on the financial implications of entering emerging markets, and a case study of a company that successfully scaled globally.",
            "Host a discussion on innovation in the digital age with CTO Dr. Emma White and innovation expert Richard Yang. Include perspectives from a guest entrepreneur who disrupted their industry with innovative solutions.",
            "Produce a podcast on sustainability where Chief Sustainability Officer Anna Davis explores how Prosus is integrating sustainable practices into its business model with environmental economist Dr. James Stone. Feature a segment with a company successfully implementing sustainable initiatives.",
            "Check recent case studies on digital transformation and create a podcast for C-level executives exploring how global companies are leading digital innovation. Feature interviews with industry leaders and insights from recent success stories."
        ]
    },
    {
        "id": 3,
        "title": "E-commerce - FAQ on Products",
        "icon": "heroicons-outline:globe-alt",
        "messages": [
            "Craft an audio scenario where an AI assistant handles a call from an unhappy customer, Sarah, who is frustrated about a delayed delivery. The AI assistant calmly explains the situation, provides updates, and offers compensation to ease Sarah's frustration, ensuring a positive resolution.",
            "Develop an audio interaction where a customer service AI assistant helps a dissatisfied customer, Mark, with returning a product. The AI assistant guides Mark through the return process, answers his questions, and reassures him about the next steps."
        ]
    },
    {
        "id": 4,
        "title": "E-commerce - Promotional Audio",
        "icon": "heroicons-outline:volume-up",
        "messages": [
            "Produce a promotional segment for a new e-commerce platform, featuring tech enthusiast Mark highlighting the platform's cutting-edge features. Include a happy customer, Emily, sharing her user experience, and tech expert Dr. Kim providing an in-depth analysis of the platform’s unique benefits.",
            "Generate a radio spot for an online food delivery service where head chef Antonio describes the exquisite menu available through the platform. Include testimonials from satisfied customers and a food critic offering a glowing review of the service.",
            "Search for the latest trends in e-commerce and develop a promotional podcast highlighting how the platform is staying ahead of the curve. Feature interviews with industry experts and testimonials from early adopters."
        ]
    },
    {
        "id": 5,
        "title": "Education - Transformers",
        "icon": "heroicons-outline:beaker",
        "messages": [
            "Develop an introductory course episode where AI educator Dr. Emily Chen explains the basics of transformers using simple analogies and relatable examples, making the complex technology behind GPT accessible to everyone.",
            "Produce an episode where AI expert Dr. Alex Carter explores real-world applications of transformers, such as chatbots and virtual assistants, using case studies and practical examples.",
            "Research the latest advancements in transformer models and create an educational podcast episode that explains these innovations in layman's terms. Include interviews with AI researchers and practical examples of how these models are being used."
        ]
    },
    {
        "id": 6,
        "title": "Education - Financial Literacy",
        "icon": "heroicons-outline:sparkles",
        "messages": [
            "Host a podcast episode where financial advisor Sarah Kim shares practical budgeting tips, including real-life scenarios and a case study of a listener who successfully managed their finances. Include expert advice on the psychological benefits of financial planning.",
            "Create an engaging podcast episode where a finance professor discusses the basics of investing, featuring interviews with individuals who improved their credit score and financial health. Include a Q&A segment where listeners submit questions for live expert advice.",
            "Check recent trends in personal finance and develop a podcast that explores new strategies for saving and investing in a post-pandemic world. Include expert interviews and practical advice to help listeners navigate the current economic climate."
        ]
    }
  ]
});

const getters = {
  allExamples: (state) => state.examples
};

export default {
  namespaced: true,
  state,
  getters
};
