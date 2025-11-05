import { usePlugins } from "@logics_configs";
import { ErrorBoundary } from "react-error-boundary";

export const PluginHost = ({ render_components }) => {
    const { setErrorPlugin } = usePlugins();

    return (
        <>
            {render_components.map((plugin, index) => {
                const PluginComponent = plugin.component;
                const plugin_id = plugin.plugin_id;

                return PluginComponent ? (
                    <ErrorBoundary
                        key={plugin_id || index}
                        fallbackRender={() => null}
                        onError={(_error, _info) => {
                            // Disable the plugin on error
                            setErrorPlugin(plugin_id, "disabled_due_to_an_error");
                        }}
                    >
                        <PluginComponent />
                    </ErrorBoundary>
                ) : null;
            })}
        </>
    );
};