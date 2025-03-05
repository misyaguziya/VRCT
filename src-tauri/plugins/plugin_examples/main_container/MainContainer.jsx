

export const MainContainer = ({useStore_CountPluginState}) => {
    const { updateCountPluginState, currentCountPluginState } = useStore_CountPluginState();
    const incrementCount = () => {
        updateCountPluginState((prev_value) => {
            return { count: prev_value.data.count + 1 }
        });
    };

    return (
        <div>
            <p>Dev Plugin Count: {currentCountPluginState?.data?.count}</p>
            <button onClick={incrementCount}>
                Increment Plugin Count
            </button>
        </div>
    );
};