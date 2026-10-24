import Header from '../components/layout/Header';
import SaveBar from '../components/layout/SaveBar';
import DeviationForm from '../components/deviation/DeviationForm';
import AICopilot from '../components/copilot/AICopilot';

export default function DeviationPage() {
  return (
    <div className="app-shell">
      <Header />
      <div className="workspace">
        <div className="workspace__form-column">
          <DeviationForm />
        </div>
        <div className="workspace__copilot-column">
          <AICopilot />
        </div>
      </div>
      <SaveBar />
    </div>
  );
}
