import { Link } from "react-router-dom";
import type { ReactNode } from "react";

function Doc({ title, children }: { title: string; children: ReactNode }) {
  return <div className="mx-auto max-w-3xl px-4 py-10"><Link to="/" className="text-sm text-brand-600">← SmartBusiness AI</Link>
    <h1 className="mt-4 text-3xl font-bold">{title}</h1>
    <div className="prose mt-6 space-y-4 text-slate-700 [&_h2]:mt-6 [&_h2]:text-xl [&_h2]:font-semibold [&_li]:ml-5 [&_li]:list-disc">{children}</div>
    <p className="mt-10 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Modelo de referência. Antes de operar comercialmente, complete os dados do responsável pelo tratamento e revise com um profissional jurídico do seu país.</p>
  </div>;
}

export function Privacy() {
  return <Doc title="Política de privacidade">
    <p>Esta política explica como a SmartBusiness AI trata dados pessoais, em conformidade com o Regulamento Geral sobre a Proteção de Dados (RGPD – UE 2016/679).</p>
    <h2>Papéis</h2>
    <p>Para os dados da conta (empresário e funcionários), a SmartBusiness AI é <b>responsável pelo tratamento</b>. Para os dados dos clientes finais que conversam com o agente, a empresa cliente é a responsável e a SmartBusiness AI atua como <b>subcontratante (operador)</b>.</p>
    <h2>Dados tratados</h2>
    <ul><li>Conta: nome, e-mail, senha (armazenada apenas como hash bcrypt), dados de faturamento processados pela Stripe.</li>
      <li>Clientes finais: identificador do canal (número de WhatsApp, ID de chat do Telegram ou sessão do site), nome, telefone e e-mail informados voluntariamente, mensagens, agendamentos, pedidos de orçamento e o registro de consentimento para mensagens comerciais.</li></ul>
    <h2>Finalidades e bases legais</h2>
    <ul><li>Prestação do serviço de atendimento automatizado (execução de contrato).</li><li>Faturamento e obrigações fiscais (obrigação legal).</li><li>Segurança, prevenção de abuso e limitação de taxa (interesse legítimo).</li><li>Mensagens comerciais aos clientes finais somente com consentimento explícito, revogável a qualquer momento.</li></ul>
    <h2>Subcontratantes</h2>
    <ul><li>OpenAI (geração de respostas), Stripe (pagamentos), Meta (WhatsApp), Telegram, Render (hospedagem e banco de dados), provedor de e-mail transacional. Transferências para fora do EEE ocorrem com base em cláusulas contratuais-tipo.</li></ul>
    <h2>Conservação</h2>
    <p>Os dados ficam armazenados enquanto a conta estiver ativa. Ao excluir a conta, todos os dados da empresa e dos seus clientes finais são apagados imediatamente do banco de dados principal; cópias de segurança expiram conforme o ciclo de retenção do provedor.</p>
    <h2>Seus direitos</h2>
    <p>Acesso, retificação, apagamento, portabilidade, oposição e limitação. No painel, em <b>Conta</b>, é possível exportar todos os dados (JSON) e excluir a conta. Cada empresa pode exportar ou apagar os dados de um cliente final no CRM. Você também pode apresentar reclamação à autoridade de proteção de dados (ex.: CNIL na França, CNPD em Portugal).</p>
    <h2>Segurança</h2>
    <p>Isolamento de dados por empresa, HTTPS, senhas com hash, tokens de integração criptografados (AES-256-GCM), verificação de assinatura de webhooks e limitação de taxa.</p>
  </Doc>;
}

export function Terms() {
  return <Doc title="Termos de uso">
    <p>Ao criar uma conta você concorda com estes termos.</p>
    <h2>Serviço</h2><p>A SmartBusiness AI fornece um agente de IA que responde clientes com base nas informações cadastradas pela empresa. A empresa é responsável pela exatidão das informações (preços, horários, serviços) e por revisar as conversas.</p>
    <h2>Limitações da IA</h2><p>Respostas geradas por IA podem conter erros. O agente é configurado para não inventar informações e para transferir para atendimento humano quando necessário, mas não substitui a supervisão da empresa.</p>
    <h2>Uso aceitável</h2><p>É proibido usar o serviço para spam, mensagens comerciais sem consentimento, conteúdo ilegal ou violação das políticas da Meta, do Telegram e da OpenAI. Contas abusivas podem ser bloqueadas.</p>
    <h2>Assinaturas</h2><p>Planos pagos são cobrados mensalmente via Stripe, com renovação automática. O cancelamento pode ser feito a qualquer momento no painel e vale ao fim do período pago. O plano gratuito é um teste de 7 dias.</p>
    <h2>Integrações de terceiros</h2><p>O uso do WhatsApp requer conta Meta Business e aceitação dos termos da Meta; o Telegram requer um bot criado pela própria empresa. A disponibilidade destas plataformas não depende da SmartBusiness AI.</p>
  </Doc>;
}
