/**
 * Modelos de agente por setor. Cada modelo define o fluxo de atendimento e
 * perguntas sugeridas. Os modelos NUNCA trazem preços: preços e serviços vêm
 * apenas do que a empresa cadastrar.
 */
export interface AgentTemplate {
  id: string;
  label: string;
  flow: string; // instruções de fluxo de atendimento específicas do setor
  qualifyingQuestions: string[];
  suggestedFaqs: string[]; // perguntas sugeridas para a empresa responder
  usesBooking: boolean;
  usesQuotes: boolean;
}

export const TEMPLATES: AgentTemplate[] = [
  {
    id: "restaurant", label: "Restaurante", usesBooking: true, usesQuotes: false,
    flow: "Ajude com cardápio, horários e reservas de mesa. Para reservar, pergunte data, horário, número de pessoas e nome. Para eventos/grupos grandes, ofereça transferir para um humano.",
    qualifyingQuestions: ["Para quantas pessoas?", "Para qual data e horário?", "Alguma restrição alimentar?"],
    suggestedFaqs: ["Vocês têm opções vegetarianas?", "Aceitam reservas para grupos?", "Têm estacionamento?"],
  },
  {
    id: "hairdresser", label: "Cabeleireiro", usesBooking: true, usesQuotes: false,
    flow: "Ajude a escolher o serviço (corte, coloração, escova etc.) e agende. Pergunte o serviço desejado, data/horário preferido e nome.",
    qualifyingQuestions: ["Qual serviço deseja?", "Tem preferência de dia e horário?"],
    suggestedFaqs: ["Quanto tempo dura uma coloração?", "Preciso levar algo?", "Qual a política de cancelamento?"],
  },
  {
    id: "barber", label: "Barbearia", usesBooking: true, usesQuotes: false,
    flow: "Agende cortes e barba. Pergunte o serviço, data/horário e nome. Seja direto e descontraído se a personalidade permitir.",
    qualifyingQuestions: ["Corte, barba ou os dois?", "Qual dia e horário prefere?"],
    suggestedFaqs: ["Atendem sem hora marcada?", "Quais formas de pagamento?"],
  },
  {
    id: "cleaning", label: "Empresa de limpeza", usesBooking: false, usesQuotes: true,
    flow: "Qualifique o pedido e crie um pedido de orçamento: tipo de imóvel, metragem aproximada, frequência, endereço/bairro e contato. Nunca invente preço; diga que a equipe enviará o orçamento.",
    qualifyingQuestions: ["Residencial ou comercial?", "Qual a metragem aproximada?", "Com que frequência?", "Em qual bairro/cidade?"],
    suggestedFaqs: ["Vocês levam os produtos?", "Atendem aos finais de semana?"],
  },
  {
    id: "real_estate", label: "Imobiliária", usesBooking: true, usesQuotes: true,
    flow: "Identifique se o cliente quer comprar, alugar ou vender, orçamento, região e número de quartos. Registre como potencial cliente e ofereça agendar uma visita ou contato com um corretor.",
    qualifyingQuestions: ["Comprar, alugar ou vender?", "Qual região?", "Qual faixa de orçamento?", "Quantos quartos?"],
    suggestedFaqs: ["Quais documentos preciso para alugar?", "Vocês fazem avaliação de imóveis?"],
  },
  {
    id: "garage", label: "Oficina / Garagem", usesBooking: true, usesQuotes: true,
    flow: "Pergunte marca, modelo, ano do veículo e o problema/serviço. Para revisões, agende. Para reparos, crie pedido de orçamento — nunca estime preço de reparo sem dados cadastrados.",
    qualifyingQuestions: ["Qual a marca, modelo e ano do veículo?", "Qual o problema ou serviço?"],
    suggestedFaqs: ["Fazem revisão de garantia?", "Quanto tempo leva uma revisão?"],
  },
  {
    id: "gym", label: "Academia", usesBooking: true, usesQuotes: false,
    flow: "Apresente modalidades e planos cadastrados, ofereça aula experimental (agendamento) e registre o objetivo do cliente.",
    qualifyingQuestions: ["Qual o seu objetivo?", "Que horários costuma treinar?"],
    suggestedFaqs: ["Tem aula experimental?", "Qual o horário de funcionamento aos feriados?"],
  },
  {
    id: "hotel", label: "Hotel", usesBooking: false, usesQuotes: true,
    flow: "Informe sobre quartos, serviços e políticas cadastrados. Para reservas, colete datas de entrada/saída, número de hóspedes e tipo de quarto e crie um pedido (a disponibilidade real é confirmada pela recepção). Nunca confirme disponibilidade por conta própria.",
    qualifyingQuestions: ["Datas de entrada e saída?", "Quantos hóspedes?", "Tipo de quarto?"],
    suggestedFaqs: ["Qual o horário de check-in e check-out?", "Aceitam animais?", "Café da manhã incluso?"],
  },
  {
    id: "ecommerce", label: "Loja online", usesBooking: false, usesQuotes: true,
    flow: "Ajude com produtos, prazos de entrega, trocas e devoluções conforme as políticas cadastradas. Para status de pedido, peça o número e transfira para um humano (sem acesso ao sistema da loja).",
    qualifyingQuestions: ["Qual produto procura?", "Para qual CEP/cidade seria a entrega?"],
    suggestedFaqs: ["Qual o prazo de entrega?", "Como funciona a troca?", "Quais formas de pagamento?"],
  },
  {
    id: "gardening", label: "Jardinagem", usesBooking: true, usesQuotes: true,
    flow: "Qualifique: tipo de serviço (manutenção, poda, paisagismo), tamanho da área, frequência e endereço. Crie pedido de orçamento ou agende uma visita técnica.",
    qualifyingQuestions: ["Qual serviço precisa?", "Tamanho aproximado da área?", "Qual o endereço/bairro?"],
    suggestedFaqs: ["Recolhem os resíduos verdes?", "Fazem contrato mensal?"],
  },
  {
    id: "services", label: "Prestador de serviços", usesBooking: true, usesQuotes: true,
    flow: "Entenda a necessidade do cliente, recomende o serviço cadastrado mais adequado e crie um pedido de orçamento ou um agendamento.",
    qualifyingQuestions: ["Do que você precisa?", "Para quando?"],
    suggestedFaqs: ["Atendem em qual região?", "Como funciona o pagamento?"],
  },
];

export const getTemplate = (id: string) => TEMPLATES.find((t) => t.id === id) ?? TEMPLATES[TEMPLATES.length - 1];
