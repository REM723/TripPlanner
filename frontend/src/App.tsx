import { BudgetRevisionPrompt } from './components/BudgetRevisionPrompt/BudgetRevisionPrompt';
import { DestinationSuggester } from './components/DestinationSuggester/DestinationSuggester';
import { InputForm } from './components/InputForm/InputForm';
import { RegenerateControl } from './components/RegenerateControl';
import { ResultsView } from './components/Results/ResultsView';
import { usePlannerMachine } from './state/plannerMachine';

function App() {
  const { state, submit, confirmDestination, editInput, retry } = usePlannerMachine();

  return (
    <div className="min-h-dvh">
      {state.step === 'input' && (
        <div className="flex h-dvh items-center justify-center gap-4 overflow-y-auto">
          <img src="/Side.jpg" alt="" className="hidden h-dvh w-1/4 object-cover lg:block" />
          <InputForm initialValue={state.initialInput} onSubmit={submit} />
          <img src="/side2.jpg" alt="" className="hidden h-dvh w-1/4 object-cover lg:block" />
        </div>
      )}

      {state.step === 'submitting' && (
        <div className="mx-auto max-w-2xl px-4 py-20 text-center text-ink-muted">Building your trip plan...</div>
      )}

      {state.step === 'destinationSuggesting' && (
        <>
          <DestinationSuggester
            recommended={state.result.status === 'ok' ? state.result.tripSummary.destination : state.result.destination}
            alternatives={state.result.suggestedDestinations}
            onConfirm={confirmDestination}
            onChooseDifferent={(destination) => submit({ ...state.lastInput, destination })}
          />
          <EditInputsLink onEdit={editInput} />
        </>
      )}

      {state.step === 'budgetRevision' && (
        <>
          <BudgetRevisionPrompt result={state.result} lastInput={state.lastInput} onResubmit={submit} />
          <EditInputsLink onEdit={editInput} />
        </>
      )}

      {state.step === 'results' && (
        <>
          <RegenerateControl destination={state.result.tripSummary.destination} onEdit={editInput} />
          <ResultsView plan={state.result} />
        </>
      )}

      {state.step === 'requestFailed' && (
        <div className="mx-auto max-w-2xl px-4 py-20 text-center">
          <p className="text-danger">{state.message}</p>
          <button type="button" onClick={retry} className="mt-4 rounded-lg bg-accent px-4 py-2 font-medium text-white">
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

function EditInputsLink({ onEdit }: { onEdit: () => void }) {
  return (
    <div className="mx-auto max-w-2xl px-4 pb-10 text-center">
      <button type="button" onClick={onEdit} className="text-sm text-ink-muted underline">
        Start over with different inputs
      </button>
    </div>
  );
}

export default App;
