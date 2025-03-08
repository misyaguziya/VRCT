import { useStore } from "../store/store";

export const MainContainer = () => {
    const { updateCountPluginState, currentCountPluginState } = useStore("useStore_CountPluginState");

    const incrementCount = () => {
        updateCountPluginState((prev_value) => ({
            count: prev_value.data.count + 1,
        }));
    };

    return (
        <div>
            <p>1 Zipped Dev Plugin Count: {currentCountPluginState?.data?.count}</p>
            <button onClick={incrementCount}>Increment Plugin Count</button>
        </div>
    );
};