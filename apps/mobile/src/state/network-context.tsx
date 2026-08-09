import NetInfo from "@react-native-community/netinfo";
import { onlineManager } from "@tanstack/react-query";
import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useState,
} from "react";

const NetworkContext = createContext(true);

export function NetworkProvider({ children }: PropsWithChildren) {
  const [online, setOnline] = useState(true);

  useEffect(
    () =>
      NetInfo.addEventListener((state) => {
        const nextOnline =
          state.isConnected !== false && state.isInternetReachable !== false;
        setOnline(nextOnline);
        onlineManager.setOnline(nextOnline);
      }),
    [],
  );

  return (
    <NetworkContext.Provider value={online}>{children}</NetworkContext.Provider>
  );
}

export function useIsOnline() {
  return useContext(NetworkContext);
}
