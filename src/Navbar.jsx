import { Fragment } from 'react'
import { useNavigate } from 'react-router-dom';
import { Disclosure, Menu, Transition } from '@headlessui/react'
import { BellIcon, Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'

const navigation = [
  { name: 'Dashboard', href: '#', current: true },
  { name: 'Team', href: '#', current: false },
  { name: 'Projects', href: '#', current: false },
  { name: 'Calendar', href: '#', current: false },
]

import { UserIcon } from '@heroicons/react/24/solid'

export default function Navbar({ sidebarExpanded, user, setUser, onLogout }) {
  const navigate = useNavigate();
  function classNames(...classes) {
    return classes.filter(Boolean).join(' ')
  }

  return (
  <Disclosure as="nav" className="bg-gradient-to-r from-black via-gray-900 to-black/80 backdrop-blur-lg shadow-[0_4px_32px_0_rgba(255,255,255,0.10)] w-full transition-all duration-300 border-b border-white/10">
      {({ open }) => (
        <>
          <div className={`mx-auto px-2 sm:px-4 lg:px-8 transition-all duration-300 w-full`}> {/* Responsive padding */}
            <div className={`flex h-16 items-center justify-end transition-all duration-300 w-full`}>
              <div className="hidden md:block">
                <div className="ml-4 flex items-center md:ml-6">
                  <button
                    type="button"
                    className="rounded-full bg-white/20 p-2 text-white hover:bg-white/30 shadow-md focus:outline-none"
                  >
                    <span className="sr-only">View notifications</span>
                    <BellIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                  {/* Add space between notification and login/profile button */}
                  <span className="mx-2" />
                  {/* Profile dropdown or login icon */}
                  {!user ? (
                    <button
                      type="button"
                      className="rounded-full bg-white/20 p-2 text-white shadow-md focus:outline-none flex items-center justify-center"
                      // ...existing code...
                    >
                      <UserIcon className="h-6 w-6 text-white" />
                    </button>
                  ) : (
                    <Menu as="div" className="relative ml-3">
                      <div>
                        <Menu.Button className="flex max-w-xs items-center rounded-full bg-white/20 text-sm focus:outline-none shadow-md">
                          <span className="sr-only">Open user menu</span>
                          <img
                            className="h-8 w-8 rounded-full border-2 border-white/40 shadow"
                            src={user.imageUrl || "https://randomuser.me/api/portraits/men/32.jpg"}
                            alt="Profile"
                          />
                        </Menu.Button>
                      </div>
                      <Transition
                        as={Fragment}
                        enter="transition ease-out duration-100"
                        enterFrom="transform opacity-0 scale-95"
                        enterTo="transform opacity-100 scale-100"
                        leave="transition ease-in duration-75"
                        leaveFrom="transform opacity-100 scale-100"
                        leaveTo="transform opacity-0 scale-95"
                      >
                        <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-xl bg-white/80 backdrop-blur-lg py-1 shadow-xl ring-1 ring-black ring-opacity-5 focus:outline-none">
                          <div className="px-4 py-2 border-b border-gray-200 flex flex-col items-center">
                            <div className="text-base font-semibold text-gray-900 text-center w-full">{user.name}</div>
                            <div className="text-sm text-gray-600">{user.email}</div>
                          </div>
                          <Menu.Item>
                            {({ active }) => (
                              <a
                                href="#"
                                className={classNames(active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700')}
                                onClick={() => {
                                  onLogout();
                                  navigate('/');
                                }}
                              >
                                Sign out
                              </a>
                            )}
                          </Menu.Item>
                        </Menu.Items>
                      </Transition>
                    </Menu>
                  )}
                </div>
              </div>
              <div className="-mr-2 flex md:hidden">
                {/* Mobile menu button */}
                <Disclosure.Button className="inline-flex items-center justify-center rounded-md bg-white/20 p-2 text-white hover:bg-white/30 shadow-md focus:outline-none">
                  <span className="sr-only">Open main menu</span>
                  {open ? (
                    <XMarkIcon className="block h-6 w-6" aria-hidden="true" />
                  ) : (
                    <Bars3Icon className="block h-6 w-6" aria-hidden="true" />
                  )}
                </Disclosure.Button>
              </div>
            </div>
          </div>
          <Disclosure.Panel className="md:hidden">
            <div className="space-y-1 px-2 pb-3 pt-2">
              {navigation.map((item) => (
                <Disclosure.Button
                  key={item.name}
                  as="a"
                  href={item.href}
                  className={classNames(
                    item.current ? 'bg-gray-900 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white',
                    'block px-3 py-2 rounded-md text-base font-medium'
                  )}
                  aria-current={item.current ? 'page' : undefined}
                >
                  {item.name}
                </Disclosure.Button>
              ))}
            </div>
          </Disclosure.Panel>
        </>
      )}
    </Disclosure>
  )
}
